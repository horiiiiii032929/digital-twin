import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { OfficeHours } from './office-hours.mjs';
import {
  Stack, Duration, Size, RemovalPolicy, CfnOutput, CfnParameter, Tags,
  aws_ec2 as ec2, aws_iam as iam, aws_cloudfront as cloudfront,
  aws_cloudfront_origins as origins, aws_ecr_assets as images,
  aws_s3_assets as assets, aws_secretsmanager as secrets,
  aws_ssm as ssm, aws_logs as logs, aws_backup as backup,
  aws_cloudwatch as cloudwatch, aws_events as events,
} from 'aws-cdk-lib';

const base = resolve(dirname(fileURLToPath(import.meta.url)), '..');

export class DigitalTwinStack extends Stack {
  constructor(scope, id, props = {}) {
    super(scope, id, props);
    Tags.of(this).add('Project', 'digital-twin');
    Tags.of(this).add('Environment', 'pilot');
    const vpc = new ec2.Vpc(this, 'Vpc', {
      maxAzs: 1, natGateways: 1,
      subnetConfiguration: [
        { name: 'egress', subnetType: ec2.SubnetType.PUBLIC, cidrMask: 24 },
        { name: 'runtime', subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS, cidrMask: 24 },
      ],
    });
    const group = new ec2.SecurityGroup(this, 'RuntimeSecurityGroup', { vpc });
    // AWS's documented origin-facing prefix list is required even for this private origin.
    // Verified in ap-southeast-1; parameterized for explicit future regional changes.
    const originPrefixList = new CfnParameter(this, 'CloudFrontPrefixListId', {
      type: 'String', default: 'pl-31a34658', allowedPattern: '^pl-[0-9a-f]+$',
      description: 'Singapore com.amazonaws.global.cloudfront.origin-facing managed prefix list',
    });
    group.addIngressRule(ec2.Peer.prefixList(originPrefixList.valueAsString), ec2.Port.tcp(80), 'CloudFront origin-facing traffic');
    const role = new iam.Role(this, 'HostRole', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore')],
    });
    const existingSecretArn = this.node.tryGetContext('runtimeSecretArn');
    const runtimeSecret = existingSecretArn
      ? secrets.Secret.fromSecretCompleteArn(this, 'RuntimeSecret', existingSecretArn)
      : new secrets.Secret(this, 'RuntimeSecret', {
      description: 'Set OPENAI_API_KEY before running the deployment document; preserve the generated HMAC secret.',
      generateSecretString: {
        secretStringTemplate: JSON.stringify({ OPENAI_API_KEY: '' }),
        generateStringKey: 'APP_LEARNING_GAP_HMAC_SECRET', passwordLength: 64, excludePunctuation: true,
      },
      removalPolicy: RemovalPolicy.RETAIN,
    });
    runtimeSecret.grantRead(role);
    const logGroup = new logs.LogGroup(this, 'RuntimeLogs', {
      retention: logs.RetentionDays.ONE_MONTH, removalPolicy: RemovalPolicy.RETAIN,
    });
    logGroup.grantWrite(role);
    const volume = new ec2.Volume(this, 'RuntimeData', {
      availabilityZone: vpc.privateSubnets[0].availabilityZone,
      size: Size.gibibytes(requireSize(this.node.tryGetContext('dataGiB') ?? 80)),
      volumeType: ec2.EbsDeviceVolumeType.GP3, encrypted: true,
      removalPolicy: RemovalPolicy.RETAIN,
    });
    const host = new ec2.Instance(this, 'Host', {
      vpc, vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroup: group, role,
      instanceType: new ec2.InstanceType('c7i-flex.large'),
      // Preserve the existing pilot host during app releases. OS upgrades require
      // an explicit maintenance/restore plan, not a moving SSM latest-AMI value.
      machineImage: ec2.MachineImage.genericLinux({ 'ap-southeast-1': 'ami-0872fceefd41a6357' }),
      requireImdsv2: true,
      blockDevices: [{ deviceName: '/dev/xvda', volume: ec2.BlockDeviceVolume.ebs(30, {
        encrypted: true, volumeType: ec2.EbsDeviceVolumeType.GP3,
      }) }],
    });
    new ec2.CfnVolumeAttachment(this, 'DataAttachment', {
      instanceId: host.instanceId, volumeId: volume.volumeId, device: '/dev/sdf',
    });
    const officeHours = new OfficeHours(this, 'OfficeHours', { instanceId: host.instanceId });
    host.addUserData(
      'set -euo pipefail',
      'dnf install -y docker jq',
      'systemctl enable --now docker',
      `VOLUME_ID=${volume.volumeId}`,
      'DEVICE=/dev/disk/by-id/nvme-Amazon_Elastic_Block_Store_${VOLUME_ID//-/}',
      'for attempt in $(seq 1 120); do [ -b "$DEVICE" ] && break; sleep 5; done',
      'test -b "$DEVICE"',
      'blkid "$DEVICE" || mkfs.ext4 "$DEVICE"',
      'mkdir -p /var/lib/digital-twin /opt/digital-twin',
      'UUID=$(blkid -s UUID -o value "$DEVICE")',
      'echo "UUID=$UUID /var/lib/digital-twin ext4 defaults 0 2" >> /etc/fstab',
      'mount /var/lib/digital-twin',
      'chown 10001:10001 /var/lib/digital-twin',
      // Do not let Docker start applications on an empty root-disk directory after reboot.
      'mkdir -p /etc/systemd/system/docker.service.d',
      'printf "[Unit]\\nRequiresMountsFor=/var/lib/digital-twin\\n" > /etc/systemd/system/docker.service.d/runtime.conf',
      'systemctl daemon-reload',
    );
    const distribution = new cloudfront.Distribution(this, 'Distribution', {
      comment: 'Digital Twin pilot — AWS hostname, authenticated same-origin app',
      defaultBehavior: {
        origin: origins.VpcOrigin.withEc2Instance(host, {
          protocolPolicy: cloudfront.OriginProtocolPolicy.HTTP_ONLY,
          readTimeout: Duration.seconds(60),
        }),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
        cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
        originRequestPolicy: cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
        responseHeadersPolicy: cloudfront.ResponseHeadersPolicy.SECURITY_HEADERS,
        compress: true,
      },
      priceClass: cloudfront.PriceClass.PRICE_CLASS_200,
      errorResponses: [403, 404, 500, 502, 503, 504].map(httpStatus => ({ httpStatus, ttl: Duration.seconds(0) })),
    });
    // Building/publishing these assets happens at deploy, never during synthesis.
    const assetProps = { directory: resolve(base, '.build-context'), file: 'deploy/Dockerfile', platform: images.Platform.LINUX_AMD64 };
    const api = new images.DockerImageAsset(this, 'ApiImage', { ...assetProps, target: 'api' });
    const web = new images.DockerImageAsset(this, 'WebImage', { ...assetProps, target: 'web', buildArgs: { VITE_AUTH_MODE: 'session', VITE_API_BASE_URL: '' } });
    api.repository.grantPull(role);
    web.repository.grantPull(role);
    const bundle = new assets.Asset(this, 'RuntimeBundle', {
      path: resolve(base, 'runtime'), exclude: ['**/__pycache__/**', '**/*.pyc', '.env*', '**/.env*'],
    });
    bundle.grantRead(role);
    const document = new ssm.CfnDocument(this, 'DeployRelease', {
      documentType: 'Command', documentFormat: 'JSON', updateMethod: 'NewVersion',
      content: {
        schemaVersion: '2.2',
        description: 'Install the pinned R1 release. Fails before stopping containers if the API secret or storage is absent.',
        mainSteps: [{ action: 'aws:runShellScript', name: 'deploy', inputs: {
          timeoutSeconds: '1800', runCommand: [
            '#!/bin/bash', 'set -euo pipefail', 'umask 077',
            'command -v docker', 'mountpoint -q /var/lib/digital-twin',
            `aws s3 cp '${bundle.s3ObjectUrl}' /opt/digital-twin/runtime.zip --region '${this.region}'`,
            'python3 -m zipfile -e /opt/digital-twin/runtime.zip /opt/digital-twin/release',
            `export AWS_REGION='${this.region}'`,
            `export RUNTIME_SECRET_ARN='${runtimeSecret.secretArn}'`,
            `export APP_URL='https://${distribution.distributionDomainName}'`,
            `export API_IMAGE='${api.imageUri}'`, `export WEB_IMAGE='${web.imageUri}'`,
            `export LOG_GROUP='${logGroup.logGroupName}'`,
            'bash /opt/digital-twin/release/deploy.sh',
          ],
        } }],
      },
    });
    const vault = new backup.BackupVault(this, 'BackupVault', { removalPolicy: RemovalPolicy.RETAIN });
    const plan = new backup.BackupPlan(this, 'BackupPlan', { backupVault: vault });
    plan.addRule(new backup.BackupPlanRule({
      ruleName: 'DailyRetainedData', scheduleExpression: events.Schedule.cron({ minute: '0', hour: '18' }),
      deleteAfter: Duration.days(14),
    }));
    plan.addSelection('RuntimeData', { resources: [backup.BackupResource.fromArn(this.formatArn({ service: 'ec2', resource: 'volume', resourceName: volume.volumeId }))] });
    new cloudwatch.Alarm(this, 'HostStatusAlarm', {
      metric: new cloudwatch.Metric({ namespace: 'AWS/EC2', metricName: 'StatusCheckFailed',
        dimensionsMap: { InstanceId: host.instanceId }, statistic: 'Maximum', period: Duration.minutes(5) }),
      threshold: 1, evaluationPeriods: 2,
    });
    for (const [name, value] of Object.entries({
      AppUrl: `https://${distribution.distributionDomainName}`, InstanceId: host.instanceId,
      DataVolumeId: volume.volumeId, RuntimeSecretArn: runtimeSecret.secretArn,
      DeployDocument: document.ref, RuntimeLogGroup: logGroup.logGroupName,
      ApiImage: api.imageUri, WebImage: web.imageUri,
      ScheduleGroup: officeHours.group.ref,
      StartSchedule: officeHours.start.ref, StopSchedule: officeHours.stop.ref,
    })) new CfnOutput(this, `${name}Output`, { value });
  }
}

function requireSize(value) {
  const size = Number(value);
  if (!Number.isInteger(size) || size < 20 || size > 1024) throw new Error('dataGiB must be an integer from 20 to 1024');
  return size;
}
