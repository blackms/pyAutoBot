import regex
from urllib.parse import urlparse


class Utility:
    @staticmethod
    def get_base_uri(url):
        parsed_uri = urlparse(url)
        base_uri = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
        return base_uri.rstrip('/')

    # Other utility methods can be added here
    @staticmethod
    def clean_email(email):
        # Remove invalid characters
        email = regex.sub(r"[^a-zA-Z0-9._%+-@]", "", email)
        
        # Correct common TLD mistakes
        email = regex.sub(r"\.con\b", ".com", email)
        
        # Remove characters after TLD
        email = regex.sub(r"(\.[a-zA-Z]{2,4})[a-zA-Z]*$", r"\1", email)
        
        return email