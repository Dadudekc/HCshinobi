# autoblogger/services/wordpress_client.py

import requests
from requests.auth import HTTPBasicAuth
import logging
import configparser
import json


class WordPressClient:
    def __init__(self, config: configparser.ConfigParser):
        self.wordpress_url = config.get("wordpress", "url")
        self.username = config.get("wordpress", "username")
        self.password = config.get("wordpress", "password")
        self.auth = HTTPBasicAuth(self.username, self.password)
        self.categories = json.loads(
            config.get("wordpress", "categories", fallback="[]")
        )
        self.tags = json.loads(config.get("wordpress", "tags", fallback="[]"))
        self.status = (
            config.get("wordpress", "status", fallback="draft").strip().lower()
        )
        if self.status not in ["draft", "publish"]:
            self.status = "draft"
            logging.warning(
                f"Invalid post status '{self.status}' provided. Defaulting to 'draft'."
            )

    def post_to_wordpress(
        self, title, content, excerpt, categories, tags, image_url=None
    ):
        """
        Posts the generated blog content to a WordPress site using the REST API.
        """
        try:

            def get_or_create_term(endpoint, name):
                term_url = f"{self.wordpress_url}/{endpoint}"
                params = {"search": name}
                response = requests.get(term_url, params=params, auth=self.auth)
                if response.status_code == 200:
                    terms = response.json()
                    for term in terms:
                        if term["name"].lower() == name.lower():
                            return term["id"]
                    # Term not found, create it
                    payload = {"name": name}
                    response = requests.post(term_url, json=payload, auth=self.auth)
                    if response.status_code == 201:
                        return response.json()["id"]
                    else:
                        logging.error(
                            f"Failed to create term '{name}': {response.text}"
                        )
                else:
                    logging.error(f"Failed to get term '{name}': {response.text}")
                return None

            category_ids = [get_or_create_term("categories", cat) for cat in categories]
            tag_ids = [get_or_create_term("tags", tag) for tag in tags]

            post_data = {
                "title": title,
                "content": content,
                "excerpt": excerpt,
                "status": self.status,  # 'publish' or 'draft'
                "categories": [cid for cid in category_ids if cid],
                "tags": [tid for tid in tag_ids if tid],
            }

            if image_url:
                # Download the image
                image_response = requests.get(image_url)
                if image_response.status_code == 200:
                    # Upload the image to WordPress media library
                    media_headers = {
                        "Content-Disposition": f'attachment; filename="feature_image.jpg"',
                        "Content-Type": "image/jpeg",
                    }
                    media_data = image_response.content
                    media_response = requests.post(
                        f"{self.wordpress_url}/media",
                        data=media_data,
                        headers=media_headers,
                        auth=self.auth,
                    )
                    if media_response.status_code == 201:
                        media_id = media_response.json().get("id")
                        post_data["featured_media"] = media_id
                        logging.info("Featured image uploaded successfully.")
                    else:
                        logging.error(
                            f"Failed to upload feature image: {media_response.text}"
                        )
                else:
                    logging.error(f"Failed to download image from URL: {image_url}")

            response = requests.post(
                f"{self.wordpress_url}/posts", json=post_data, auth=self.auth
            )
            if response.status_code == 201:
                logging.info(
                    f"Blog post published to WordPress: {response.json().get('link')}"
                )
                return response.json()
            else:
                logging.error(f"Failed to publish post: {response.text}")
                return None
        except Exception as e:
            logging.error(f"Exception in post_to_wordpress: {e}")
            return None

    def update_settings(self, settings):
        """
        Updates WordPress settings based on user input.
        """
        try:
            self.categories = (
                json.loads(settings["categories"]) if settings["categories"] else []
            )
            self.tags = json.loads(settings["tags"]) if settings["tags"] else []
            self.status = (
                settings["status"].strip().lower()
                if settings["status"].strip().lower() in ["publish", "draft"]
                else "draft"
            )
            if self.status not in ["draft", "publish"]:
                self.status = "draft"
                logging.warning(
                    f"Invalid post status '{self.status}' provided. Defaulting to 'draft'."
                )
            logging.info("WordPressClient settings updated.")
        except Exception as e:
            logging.error(f"Error updating WordPressClient settings: {e}")
