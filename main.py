from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openrouter import ChatOpenRouter
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import  ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage,SystemMessage,AIMessage

load_dotenv()

embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

vectorstore= Chroma(
    persist_directory="chroma_db",
    embedding_function= embedding_model
)

retriever = vectorstore.as_retriever(
    search_type="mmr", #mmr means similarity search with maximum marginal relevance
    search_kwargs={"k": 3, "fetch_k": 10,"lambda_mult": 0.5}
)

llm = ChatOpenRouter(model="openrouter/free")


prompt = ChatPromptTemplate(
    [
        ("system",
            """You are a helpful AI assistant.
Use only the provided context to answer the question.

If the answer is not present in the context,
say: "I couldn't find the answer in the document."
"""),

   MessagesPlaceholder(variable_name="chat_history"),
   (
       
       "human",
        """Context:
{context}

Question:
{question}
"""
   )


    ]
)

if __name__ == "__main__":
    print("Rag system created!")
    print("press 0 to exit")

    chat_history = []

    while True:
        query = input("You: ")
        if query == '0':
            break
        docs = retriever.invoke(query)

        context = "\n\n".join([doc.page_content for doc in docs])

        final_prompt = prompt.invoke({
            "context": context,
            "question": query,
            "chat_history": chat_history
        })

        response = llm.invoke(final_prompt)
        print(f"\n AI: {response.content}")

        chat_history.append(HumanMessage(content=query))
        chat_history.append(AIMessage(content=response.content))