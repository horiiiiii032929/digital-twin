import { App } from 'aws-cdk-lib';
import { DigitalTwinStack } from './lib/stack.mjs';

const app = new App();
if (process.env.CDK_DEFAULT_ACCOUNT && process.env.CDK_DEFAULT_ACCOUNT !== '030334071887') {
  throw new Error('Use --profile digital-twin (expected AWS account 030334071887)');
}
new DigitalTwinStack(app, 'DigitalTwinPilot', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: 'ap-southeast-1',
  },
});
