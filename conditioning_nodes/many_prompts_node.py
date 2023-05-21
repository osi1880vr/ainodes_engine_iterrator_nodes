import os
from qtpy import QtCore
from qtpy import QtWidgets

from ainodes_frontend.base import register_node, get_next_opcode
from ainodes_frontend.base import AiNode, CalcGraphicsNode
from ainodes_frontend.node_engine.node_content_widget import QDMNodeContentWidget
from ainodes_frontend.node_engine.utils import dumpException
from ainodes_frontend import singleton as gs

"""
Always change the name of this variable when creating a new Node
Also change the names of the Widget and Node classes, as well as it's content_label_objname,
it will be used when saving the graphs.
"""

OP_NODE_MANY_PROMPTS = get_next_opcode()


class ManyPromptsWidget(QDMNodeContentWidget):
	def initUI(self):
		self.create_widgets()
		self.create_main_layout()

	def create_widgets(self):
		self.prompt = self.create_text_edit("Prompt")


@register_node(OP_NODE_MANY_PROMPTS)
class ManyPromptsNode(AiNode):
	icon = "ainodes_frontend/icons/base_nodes/in.png"
	op_code = OP_NODE_MANY_PROMPTS
	op_title = "Many Prompts Node"
	content_label_objname = "many_prompts_node"
	category = "Data"
	custom_input_socket_name = ['DONE','LOOP', "DATA", "EXEC"]

	custom_output_socket_name = ['DONE', "DATA", "EXEC"]

	def __init__(self, scene):
		super().__init__(scene, inputs=[1, 1, 6, 1], outputs=[1, 6, 1])

	def initInnerClasses(self):
		self.content = ManyPromptsWidget(self)
		self.grNode = CalcGraphicsNode(self)
		self.grNode.width = 340
		self.grNode.height = 500
		self.content.setMinimumWidth(340)
		self.content.setMinimumHeight(500)
		self.content.eval_signal.connect(self.evalImplementation)
		self.iteration_lenght = 0
		self.iteration_step = 0
		self.done = False
		self.all_done = False
		self.prompts = []
		self.stop_top_iterator = False

	def get_conditioning(self, prompt="", progress_callback=None):

		"""if gs.loaded_models["loaded"] == []:
			for node in self.scene.nodes:
				if isinstance(node, TorchLoaderNode):
					node.evalImplementation()
					#print("Node found")"""

		c = gs.models["clip"].encode(prompt)
		uc = {}
		return [[c, uc]]

	def calc_next_step(self, data):
		self.iteration_step += 1
		if self.iteration_step > self.iteration_lenght:
			self.done = True
			if self.stop_top_iterator is True:
				if not data:
					data = {}
				data['loop_done'] = True

	@QtCore.Slot()
	def evalImplementation_thread(self):
		self.busy = True
		data = None
		result = None

		if not self.all_done:

			if self.iteration_step == -1:
				return result, data

			# care for the loops to work as such, no node fucntionality yet
			if len(self.getInputs(2)) > 0: # get data from a maybe top loop
				data_node, index = self.getInput(2)
				data = data_node.getOutput(index)
			else:
				self.stop_top_iterator = True # if none make sure we dont trigger done



			# here the internal magic starts with finding out how many steps the loop will have
			if self.iteration_lenght == 0:
				self.prompts = self.content.prompt.toPlainText().split('\n')
				self.iteration_lenght = len(self.prompts) - 1

			prompt = self.prompts[self.iteration_step]
			self.test = prompt

			if data and 'loop_done' in data: # if the top loop tels us its done with its loop make sure no more done is send
				if data['loop_done'] == True:
					self.stop_top_iterator = True


			#result = [self.get_conditioning(prompt=prompt)]
			result = 'test'

		"""
		Do your magic here, to access input nodes data, use self.getInputData(index),
		this is inherently threaded, so returning the value passes it to the onWorkerFinished function,
		it's super call makes sure we clean up and safely return.

		Inputs and Outputs are listed from the bottom of the node.
		"""
		return result, data

	@QtCore.Slot(object)
	def onWorkerFinished(self, result):
		super().onWorkerFinished(None)
		self.setOutput(1, result[1])
		self.getInput(0)



		if self.done: # if this loop is finished we may have to restart if we are in a larger stacked loop

			if not self.stop_top_iterator: # if the top loop is not yet done we trigger him

				if self.iteration_step > 0: # this is the last step of this iteration, we still have to trigger the rest of the process
					self.iteration_step = -1 # but for when we come back for this we know we have to trigger top loop to get a new value from there
					print(self.test)
					self.calc_next_step(result[1])
					self.executeChild(2)
				else:
					self.done = False     # we are back from the last step process now we trigger top loop
					self.iteration_step = 0
					self.executeChild(0)

			# get the next step from the maybe top iterator if there is any
			else:
				if not self.all_done:  # if we self are not done we trigger the next
					self.all_done = True
					print(self.test)

					self.executeChild(2) # make the very last step happen
		else:
			if not self.all_done:
				print(self.test)
				self.calc_next_step(result[1])
				self.executeChild(2)