from python_workflow_definition.models import *

workflow = PythonWorkflowDefinitionWorkflow(
    version="1.0",
    nodes=[
        # Input node for initial value
        PythonWorkflowDefinitionInputNode(id=1, type="input", name="initial_x", value=1),
        PythonWorkflowDefinitionInputNode(id=2, type="input", name="initial_y", value=1),
        
        # Initial add to set up context
        PythonWorkflowDefinitionFunctionNode(id=3, type="function", value="mymodule.add"),
        
        # While loop node
        PythonWorkflowDefinitionWhileNode(
            id=4,
            type="while",
            conditionExpression="ctx.n < 8",
            bodyWorkflow=PythonWorkflowDefinitionWorkflow(
                version="1.0",
                nodes=[
                    PythonWorkflowDefinitionFunctionNode(id=1, type="function", value="mymodule.add"),
                    PythonWorkflowDefinitionFunctionNode(id=2, type="function", value="mymodule.multiply"),
                ],
                edges=[
                    PythonWorkflowDefinitionEdge(source=1, target=2, targetPort="x"),
                ]
            ),
            contextVars=["n"],
            inputPorts={"n": None},  # Will be connected via edge
            outputPorts={"n": "final_n"},
            maxIterations=10
        ),
        
        # Final add after loop
        PythonWorkflowDefinitionFunctionNode(id=5, type="function", value="mymodule.add"),
        
        # Output node
        PythonWorkflowDefinitionOutputNode(id=6, type="output", name="result"),
    ],
    edges=[
        PythonWorkflowDefinitionEdge(source=1, target=3, targetPort="x"),
        PythonWorkflowDefinitionEdge(source=2, target=3, targetPort="y"),
        PythonWorkflowDefinitionEdge(source=3, target=4, targetPort="n"),
        PythonWorkflowDefinitionEdge(source=4, sourcePort="final_n", target=5, targetPort="x"),
        PythonWorkflowDefinitionEdge(source=5, target=6),
    ]
)

breakpoint()

pass
