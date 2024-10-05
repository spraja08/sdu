import aws_cdk as core
import aws_cdk.assertions as assertions

from sdu_infra.sdu_infra_stack import SduInfraStack

# example tests. To run these tests, uncomment this file along with the example
# resource in sdu_infra/sdu_infra_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = SduInfraStack(app, "sdu-infra")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
