import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { DigitalTwinStack } from '../../infra/cdk/lib/stack.mjs';

const require = createRequire(new URL('../../infra/cdk/package.json', import.meta.url));
const { App } = require('aws-cdk-lib');
const { Template, Match } = require('aws-cdk-lib/assertions');
const stack = new DigitalTwinStack(new App(), 'TestTwin', {
  env: { account: '111111111111', region: 'ap-southeast-1' },
});
const template = Template.fromStack(stack);
const file = name => readFileSync(new URL(name, import.meta.url), 'utf8');

test('private EC2, no SSH, IMDSv2, encrypted retained data', () => {
  template.resourceCountIs('AWS::EC2::Instance', 1);
  template.hasResourceProperties('AWS::EC2::Instance', {
    InstanceType: 'c7i-flex.large',
    ImageId: 'ami-0872fceefd41a6357',
  });
  template.hasResourceProperties('AWS::EC2::LaunchTemplate', {
    LaunchTemplateData: Match.objectLike({ MetadataOptions: { HttpTokens: 'required' } }),
  });
  template.hasResource('AWS::EC2::Volume', {
    Properties: Match.objectLike({ Encrypted: true, Size: 80, VolumeType: 'gp3' }),
    DeletionPolicy: 'Retain', UpdateReplacePolicy: 'Retain',
  });
  const groups = Object.values(template.findResources('AWS::EC2::SecurityGroup'));
  for (const group of groups) {
    for (const rule of group.Properties.SecurityGroupIngress || []) {
      assert.equal(rule.FromPort, 80);
      assert.equal(rule.CidrIp, undefined);
      assert.deepEqual(rule.SourcePrefixListId, { Ref: 'CloudFrontPrefixListId' });
    }
  }
  const instance = Object.values(template.findResources('AWS::EC2::Instance'))[0];
  assert.equal(instance.Properties.NetworkInterfaces, undefined);
  template.resourceCountIs('AWS::EC2::NatGateway', 1);
});

test('AWS hostname provides HTTPS and authenticated responses are never cached', () => {
  template.resourceCountIs('AWS::Route53::RecordSet', 0);
  template.resourceCountIs('AWS::CertificateManager::Certificate', 0);
  template.resourceCountIs('AWS::CloudFront::VpcOrigin', 1);
  template.hasResourceProperties('AWS::CloudFront::Distribution', {
    DistributionConfig: Match.objectLike({
      Aliases: Match.absent(),
      DefaultCacheBehavior: Match.objectLike({
        ViewerProtocolPolicy: 'redirect-to-https',
        CachePolicyId: '4135ea2d-6df8-44a3-9df3-4b5a84be39ad',
        AllowedMethods: ['GET', 'HEAD', 'OPTIONS', 'PUT', 'PATCH', 'POST', 'DELETE'],
      }),
    }),
  });
});

test('secrets are generated server-side and retained; data backup and logs exist', () => {
  template.hasResource('AWS::SecretsManager::Secret', {
    Properties: Match.objectLike({ GenerateSecretString: Match.objectLike({
      GenerateStringKey: 'APP_LEARNING_GAP_HMAC_SECRET', PasswordLength: 64,
    }) }), DeletionPolicy: 'Retain',
  });
  template.resourceCountIs('AWS::Backup::BackupPlan', 1);
  const selection = Object.values(template.findResources('AWS::Backup::BackupSelection'))[0].Properties.BackupSelection;
  assert.equal(selection.Resources.length, 1);
  assert.match(JSON.stringify(selection.Resources), /volume/);
  template.hasResourceProperties('AWS::Backup::BackupPlan', {
    BackupPlan: Match.objectLike({ BackupPlanRule: Match.arrayWith([Match.objectLike({
      ScheduleExpression: 'cron(0 18 * * ? *)', Lifecycle: { DeleteAfterDays: 14 },
    })]) }),
  });
  template.hasResourceProperties('AWS::Logs::LogGroup', { RetentionInDays: 30 });
});

test('AWS demo explicitly selects the presentation route over retained R1 base settings', () => {
  const parse = text => Object.fromEntries(text.split('\n').filter(x => x && !x.startsWith('#')).map(x => {
    const index = x.indexOf('='); return [x.slice(0, index), x.slice(index + 1)];
  }));
  const aws = parse(file('../../infra/cdk/runtime/runtime.env'));
  const qualified = parse(file('../../deploy/local-r1.qualified.env.example'));
  for (const key of ['APP_GENERATOR_MODE', 'APP_EVIDENCE_GATE_MODE', 'APP_STUDENT_PROFILE_PATH',
    'APP_STUDENT_TUTORING_MODE', 'APP_AUTONOMY_PLANNER_MODE', 'APP_T1_QUALIFICATION_RESULT_PATH']) {
    assert.equal(aws[key], qualified[key], key);
  }
  assert.equal(aws.APP_PILOT_TUTOR_ROUTE, 'audited-presentation-v1');
  assert.match(file('../../infra/cdk/runtime/deploy.sh'), /services\.api\.app\.pilot:create_pilot_app --factory/);
  assert.equal(aws.APP_MODE, 'staging');
  assert.equal(aws.APP_SECURE_COOKIES, 'true');
  assert.equal(aws.APP_PROACTIVE_OUTREACH_WORKER_ENABLED, 'false');
  assert.equal(Object.keys(aws).some(k => /EXPERIMENTAL|POST_REPORT/.test(k)), false);
});

test('asset context excludes private datasets, environment files and research run outputs', () => {
  const manifest = JSON.parse(file('../../infra/cdk/.build-context/release-manifest.json'));
  assert.ok(manifest.files['services/api/app/main.py']);
  assert.ok(manifest.files['apps/web/src/App.tsx']);
  for (const path of Object.keys(manifest.files)) {
    assert.doesNotMatch(path, /(^|\/)(data|reports|node_modules|\.env[^/]*)(\/|$)/);
    assert.doesNotMatch(path, /\.(mp4|pdf|sqlite3|zip)$/);
  }
});

test('invalid storage sizes are rejected', () => {
  const app = new App({ context: { dataGiB: 1 } });
  assert.throws(() => new DigitalTwinStack(app, 'InvalidSize'), /dataGiB must/);
});

test('office hours use Singapore time and direct, narrowly scoped EC2 actions', () => {
  template.resourceCountIs('AWS::Scheduler::Schedule', 2);
  template.resourceCountIs('AWS::Scheduler::ScheduleGroup', 1);
  const schedules = Object.values(template.findResources('AWS::Scheduler::Schedule'));
  assert.deepEqual(schedules.map(s => s.Properties.ScheduleExpression).sort(), [
    'cron(0 18 ? * MON-FRI *)', 'cron(0 9 ? * MON-FRI *)',
  ]);
  for (const { Properties: schedule } of schedules) {
    assert.equal(schedule.State, 'ENABLED');
    assert.equal(schedule.ScheduleExpressionTimezone, 'Asia/Singapore');
    assert.deepEqual(schedule.FlexibleTimeWindow, { Mode: 'OFF' });
    assert.deepEqual(schedule.Target.RetryPolicy, { MaximumEventAgeInSeconds: 300, MaximumRetryAttempts: 2 });
    assert.ok(schedule.Target.DeadLetterConfig.Arn);
    assert.match(JSON.stringify(schedule.Target.Input), /InstanceIds/);
    assert.doesNotMatch(JSON.stringify(schedule.Target.Input), /Force|Hibernate|SkipOsShutdown/);
    assert.match(JSON.stringify(schedule.Target.Arn), /aws-sdk:ec2:(startInstances|stopInstances)/);
  }
  const roles = Object.values(template.findResources('AWS::IAM::Role')).filter(r =>
    JSON.stringify(r.Properties.AssumeRolePolicyDocument).includes('scheduler.amazonaws.com'));
  assert.equal(roles.length, 2);
  const permissions = [];
  for (const { Properties: role } of roles) {
    const trust = role.AssumeRolePolicyDocument.Statement[0];
    assert.equal(trust.Condition.StringEquals['aws:SourceAccount'], '111111111111');
    assert.ok(trust.Condition.ArnEquals['aws:SourceArn']);
    const statements = role.Policies.flatMap(p => p.PolicyDocument.Statement);
    const action = statements.find(s => String(s.Action).startsWith('ec2:'));
    permissions.push(action.Action);
    assert.match(JSON.stringify(action.Resource), /instance\//);
    assert.doesNotMatch(JSON.stringify(action.Resource), /\*/);
  }
  assert.deepEqual(permissions.sort(), ['ec2:StartInstances', 'ec2:StopInstances']);
});
