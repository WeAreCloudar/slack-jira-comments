# slack-jira-comments
## Setup

### Slack

Follow these steps to configure the slash command in Slack:

  1. Navigate to https://<your-team-domain>.slack.com/apps/manage/custom-integrations
  2. Select "Incoming Webhooks" and click on "Add Configuration".
  3. Select a default channel to post to and click on "Add Incomming Webhooks Integration".
  4. Copy the Webhook URL from the integration settings and use it in the next section.
  5. You can configure additional settings here. We also edited the following settings:
    - Descriptive Label: "Jira comments via AWS Lambda"
    - Customize Name: "Jira"
    - Customize Icon

### KMS Setup
  1. Create a KMS key - http://docs.aws.amazon.com/kms/latest/developerguide/create-keys.html.
    - `aws kms create-key --description 'lambda secrets'`
    - `aws kms create-alias --alias-name alias/lambda-secrets --target-key-id <key id>`
  2. Encrypt the token using the AWS CLI= `aws kms encrypt --key-id alias/lambda-secrets --cli-input-json '{"Plaintext": "<url>"}'`.
  3. Copy the base-64 encoded, encrypted key (CiphertextBlob) to the `ENCRYPTED_URL` variable.

### Deploying to lambda
  1. Use `pip install -r requirements.txt` to install the python dependencies.
  2. Run `create_package.sh` to create a deployment zip.
  3. Go to https://eu-west-1.console.aws.amazon.com/lambda/home?region=eu-west-1#/create?step=2 to create a new Lambda Function
  4. Fill in the name (slack-jira-comments) and description and select the "Python 2.7" runtime.
  5. Select "Upload a .ZIP file" and upload "slack-jira-comments.zip"
  6. Leave the Handler on 'lambda_function.lambda_handler' and select 'Create new role > *basic execution role' as Role.
  7. On the new page select 'Create a new IAM role' as 'IAM Role'. and 'slack_jira_comment' as Role Name. Use the following policy (Show Policy Document > Edit). You can get the ARN with `aws kms describe-key --key-id alias/lambda-secrets`
  ```
       {
          "Version": "2012-10-17",
          "Statement": [
            {
              "Effect": "Allow",
              "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
              ],
              "Resource": "arn:aws:logs:*:*:*"
            },
            {
                     "Effect": "Allow",
             "Action": [
               "kms:Decrypt"
             ],
             "Resource": [
               "<your KMS key ARN>"
             ]
           }
         ]
       }
    ```
  8. Click on 'Next' and 'Create function' to create the lambda function.  


### API Gateway Setup

  1. Select the 'API endpoints' in the AWS Lambda configuration and Add an API endpoint. Use the following settings:
    - API endpoint type: API Gateway
    - API name: LambdaServices
    - Resource name: /slack-jira-comments
    - Method: POST
    - Deployment stage: prod
    - Security: Open
  3. Open the API Gateway console and select /slack-jira-comments
  4. Click on add resource to add a resource with the following settings:
    - Resource Name: channel
    - Resource Path: /slack-jira-comments/{channel}
  5. Click on "Create Method" and add a 'POST' method with the following settings:
    - Integration Type: Lambda Function
    - Lambda Region: Your region
    - Lambda Function: slack-jira-comments
  4. Open 'Integration Request' settings. And add a mapping template:
    - Content-type: application/json
    - Mapping Template: `{ "channel": "$input.params('channel')", "body": $input.json("$") }`   
  5. Click on 'Deploy api' and update the 'prod' stage.
  6. Write down the api endpoint so you can use it in the next step.

### Jira Setup
  1. Go to https://<your-jira-server>/plugins/servlet/webhooks
  2. Click on 'Create a webhook' and use thes settings:
    - Name: "Send comments to slack"
    - Status: Enabled
    - URL: https://<api-endpoint>/slack-jira-comments/CHANNEL_NAME
    - Description: "Send comments to Slack"
    - Events: All issuues
      - Issue: updated
  
  

## Update Your Deployment

To update the deployed version, edit the code in src, run `create_package.sh` and upload `slack-jira-comments.zip` to the existing lambda function.

