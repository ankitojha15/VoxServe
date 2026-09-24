from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100
)

if __name__== "__main__":
    sample = open("data/raw/refund-policy.txt").read()
    parts = splitter.split_text(sample)
    print(f"Total chunks: {len(parts)}")
    print(f"First chunk preview: {parts[0][:200]}")