from firebase import db
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
import tensorflow as tf
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Variables to hold the models
MODEL_CONTENT = None
MODEL_COLLABORATIVE = None

def load_models():
    content_model_path = 'ContentBasedFilteringModel.keras'
    collaborative_model_path = 'CollaborativeFilteringModel.keras'
    try:
        # Load the .keras model
        content_model = tf.keras.models.load_model(content_model_path)
        collaborative_model = tf.keras.models.load_model(collaborative_model_path)        
        # Assign the loaded model to the global variable
        MODEL_CONTENT = content_model
        MODEL_COLLABORATIVE = collaborative_model
        print("Content model loaded successfully")
        return MODEL_CONTENT,MODEL_COLLABORATIVE
    except Exception as e:
        print(f"Error loading content model: {e}")

try:
    MODEL_CONTENT,MODEL_COLLABORATIVE = load_models()
except Exception as e:
    print(f"Error loading models: {e}")