import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_project.settings')
django.setup()

from clinic_ai.ai_engine.vectorstore import ClinicVectorStore

def main():
    print("Initializing Vector Store...")
    vs = ClinicVectorStore()
    print("Building FAISS Index...")
    if vs.build_index():
        print("FAISS Index built successfully at:", settings.FAISS_INDEX_PATH)
    else:
        print("Failed to build FAISS Index. Check if clinic_docs/ has files.")

if __name__ == "__main__":
    main()
