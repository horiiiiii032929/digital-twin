import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';

const aws = args => execFileSync('aws', [
  ...args, '--profile', 'digital-twin', '--region', 'ap-southeast-1', '--output', 'json',
], { encoding: 'utf8' });
const identity = JSON.parse(aws(['sts', 'get-caller-identity']));
if (identity.Account !== '030334071887') throw new Error('Unexpected account for digital-twin profile');
const output = JSON.parse(readFileSync(new URL('../cdk-outputs.json', import.meta.url), 'utf8')).DigitalTwinPilot;
if (!output?.InstanceIdOutput || !output?.DeployDocumentOutput) throw new Error('Deploy the CDK stack first');
const command = JSON.parse(aws(['ssm', 'send-command',
  '--instance-ids', output.InstanceIdOutput,
  '--document-name', output.DeployDocumentOutput, '--document-version', '$LATEST',
])).Command;
console.log(`Activation command: ${command.CommandId}`);
console.log(`Target: ${output.InstanceIdOutput}; URL: ${output.AppUrlOutput}`);
console.log('Activation is asynchronous. It fails closed until the runtime secret contains OPENAI_API_KEY.');
console.log(`aws ssm get-command-invocation --profile digital-twin --region ap-southeast-1 --command-id ${command.CommandId} --instance-id ${output.InstanceIdOutput}`);
