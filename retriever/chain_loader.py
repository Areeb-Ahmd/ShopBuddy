from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from retriever.retrieval import Retriever
from utils.model_loader import ModelLoader
from prompt_library.prompt import PROMPT_TEMPLATES

class ChainLoader:
    """
    A utility class to lazily construct, cache, and invoke the LangChain LCEL RAG chain.
    """
    def __init__(self):
        self.retriever_obj = Retriever()
        self.model_loader = ModelLoader()
        self._chain = None

    def get_chain(self):
        """
        Lazily initialize and return the cached LCEL chain singleton.
        """
        if self._chain is None:
            retriever = self.retriever_obj.load_retriever()
            prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATES["product_bot"])
            llm = self.model_loader.load_llm()

            self._chain = (
                {"context": retriever, "question": RunnablePassthrough()}
                | prompt
                | llm
                | StrOutputParser()
            )
            print("LCEL Chain initialized and cached successfully.")
        return self._chain

    def invoke(self, query: str) -> str:
        """
        Invoke the cached LCEL chain with user query.
        """
        chain = self.get_chain()
        return chain.invoke(query)
