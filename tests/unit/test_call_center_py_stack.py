import aws_cdk as core
import aws_cdk.assertions as assertions

from call_center_py.call_center_py_stack import CallCenterPyStack

# example tests. To run these tests, uncomment this file along with the example
# resource in call_center_py/call_center_py_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = CallCenterPyStack(app, "call-center-py")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
