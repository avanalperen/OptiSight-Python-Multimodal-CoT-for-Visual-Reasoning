import transformers
print("AutoModel classes:", [x for x in dir(transformers) if x.startswith("AutoModelFor")])
