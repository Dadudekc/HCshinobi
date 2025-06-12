import os
import json
import logging
import faiss
import time
from sentence_transformers import SentenceTransformer
from autoblogger.models.blog_post import BlogPost
from autoblogger.services.utils import extract_title, extract_introduction
from threading import Lock

# Constants
VECTOR_DB_DIMENSION = 768  # Should match the model's output dimension
VECTOR_DB_INDEX_FILE = "vector_store.index"
VECTOR_DB_METADATA_FILE = "vector_metadata.json"


class VectorDB:
    def __init__(
        self, index_path=VECTOR_DB_INDEX_FILE, metadata_path=VECTOR_DB_METADATA_FILE
    ):
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.index = None
        self.metadata = []
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.lock = Lock()  # Optional thread safety
        self.load_vector_db()

    def load_vector_db(self):
        """
        Loads or initializes the FAISS index and metadata.
        """
        logging.info("Loading vector database...")
        with self.lock:
            # Load FAISS index
            if os.path.exists(self.index_path):
                try:
                    self.index = faiss.read_index(self.index_path)
                    logging.info(f"FAISS index loaded from {self.index_path}.")
                except Exception as e:
                    logging.error(f"Failed to load FAISS index: {e}")
                    self.index = faiss.IndexFlatIP(
                        VECTOR_DB_DIMENSION
                    )  # Fallback to a new index
            else:
                self.index = faiss.IndexFlatIP(VECTOR_DB_DIMENSION)
                logging.info("FAISS index initialized as new.")

            # Load metadata
            if os.path.exists(self.metadata_path):
                try:
                    with open(self.metadata_path, "r", encoding="utf-8") as f:
                        self.metadata = json.load(f)
                    logging.info(f"Metadata loaded from {self.metadata_path}.")
                except Exception as e:
                    logging.error(f"Failed to load metadata: {e}")
                    self.metadata = []
            else:
                self.metadata = []
                logging.info("Metadata initialized as new.")

    def save_metadata(self):
        """
        Saves metadata to the JSON file.
        """
        try:
            with self.lock, open(self.metadata_path, "w", encoding="utf-8") as f:
                json.dump(self.metadata, f, indent=2)
            logging.info(f"Metadata saved to {self.metadata_path}.")
        except Exception as e:
            logging.error(f"Error saving metadata: {e}")

    def generate_embeddings(self, texts):
        """
        Generates embeddings for a list of texts.
        """
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings
        except Exception as e:
            logging.error(f"Error generating embeddings: {e}")
            return None

    def update_vector_db(self, output_path):
        """
        Updates the vector database with a new blog post.
        """
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                content_html = f.read()

            post_title = extract_title(content_html)
            introduction = extract_introduction(content_html)

            texts = [post_title, introduction]
            embeddings = self.generate_embeddings(texts)
            if embeddings is not None:
                with self.lock:
                    faiss.normalize_L2(embeddings)
                    self.index.add(embeddings)
                    faiss.write_index(self.index, self.index_path)

                    metadata_entry = {
                        "title": post_title,
                        "excerpt": introduction[:150],
                        "link": f"/{post_title.replace(' ', '-').lower()}/",  # Replace with actual URL if available
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    self.metadata.append(metadata_entry)
                    self.save_metadata()
                    logging.info("Vector database updated with the latest post.")
            else:
                logging.error(
                    "Failed to generate embeddings; vector database not updated."
                )
        except Exception as e:
            logging.error(f"Error updating vector database: {e}")

    def extract_blog_post(self, html_content):
        """
        Extracts title and excerpt from HTML content.
        """
        title = extract_title(html_content)
        excerpt = extract_introduction(html_content)[:150]
        return BlogPost(title=title, excerpt=excerpt)

    def search(self, query_text, k=5):
        """
        Searches the FAISS index for similar blog posts.
        Returns results with metadata.
        """
        query_embedding = self.generate_embeddings([query_text])
        if query_embedding is None or self.index is None or self.index.ntotal == 0:
            logging.warning(
                "Vector DB is not initialized or query embedding generation failed."
            )
            return []

        faiss.normalize_L2(query_embedding)
        distances, indices = self.index.search(query_embedding, k)

        results = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            meta = self.metadata[idx]
            results.append(
                {
                    "title": meta["title"],
                    "excerpt": meta["excerpt"],
                    "link": meta["link"],
                    "distance": distance,
                }
            )
        return results

    def is_initialized(self):
        """
        Checks if the vector DB is initialized and contains entries.
        """
        return self.index is not None and self.index.ntotal > 0

    def reload_vector_db(self):
        """
        Reloads the vector database after settings changes.
        """
        self.load_vector_db()
