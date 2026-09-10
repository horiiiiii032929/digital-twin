import { Construct } from 'constructs';
import {
  Stack, Duration, aws_iam as iam, aws_scheduler as scheduler,
  aws_sqs as sqs, aws_cloudwatch as cloudwatch,
} from 'aws-cdk-lib';

/** Daily power transitions; no application code or credentials in scheduled jobs. */
export class OfficeHours extends Construct {
  constructor(scope, id, { instanceId, startHour = 9, stopHour = 18, weekdays = true }) {
    super(scope, id);
    if (![startHour, stopHour].every(h => Number.isInteger(h) && h >= 0 && h <= 23) || startHour >= stopHour) {
      throw new Error('Office hours require integer hours with 0 <= startHour < stopHour <= 23');
    }
    const stack = Stack.of(this);
    const group = new scheduler.CfnScheduleGroup(this, 'Group');
    const failures = new sqs.Queue(this, 'Failures', {
      encryption: sqs.QueueEncryption.SQS_MANAGED, enforceSSL: true,
      retentionPeriod: Duration.days(14),
    });
    const instanceArn = stack.formatArn({ service: 'ec2', resource: 'instance', resourceName: instanceId });
    const days = weekdays ? 'MON-FRI' : '*';
    for (const [label, operation, permission, hour] of [
      ['Start', 'startInstances', 'ec2:StartInstances', startHour],
      ['Stop', 'stopInstances', 'ec2:StopInstances', stopHour],
    ]) {
      const role = new iam.Role(this, `${label}Role`, {
        assumedBy: new iam.ServicePrincipal('scheduler.amazonaws.com', { conditions: {
          StringEquals: { 'aws:SourceAccount': stack.account },
          ArnEquals: { 'aws:SourceArn': group.attrArn },
        } }),
        inlinePolicies: { Execute: new iam.PolicyDocument({ statements: [
          new iam.PolicyStatement({ actions: [permission], resources: [instanceArn] }),
          new iam.PolicyStatement({ actions: ['sqs:SendMessage'], resources: [failures.queueArn] }),
        ] }) },
      });
      const schedule = new scheduler.CfnSchedule(this, label, {
        groupName: group.ref, state: 'ENABLED',
        description: `${label} the Digital Twin host at ${hour}:00 Asia/Singapore`,
        scheduleExpression: `cron(0 ${hour} ? * ${days} *)`,
        scheduleExpressionTimezone: 'Asia/Singapore',
        flexibleTimeWindow: { mode: 'OFF' },
        target: {
          arn: `arn:${stack.partition}:scheduler:::aws-sdk:ec2:${operation}`,
          roleArn: role.roleArn,
          input: stack.toJsonString({ InstanceIds: [instanceId] }),
          retryPolicy: { maximumEventAgeInSeconds: 300, maximumRetryAttempts: 2 },
          deadLetterConfig: { arn: failures.queueArn },
        },
      });
      this[label.toLowerCase()] = schedule;
    }
    this.group = group;
    new cloudwatch.Alarm(this, 'FailedTransitions', {
      metric: failures.metricApproximateNumberOfMessagesVisible({ period: Duration.minutes(5) }),
      threshold: 1, evaluationPeriods: 1,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
  }
}
