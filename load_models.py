# import tensorflow as tf
# # Variables to hold the models
# model_content = None
# model_collaborative = None

# def load_models():
#     global model_content, model_collaborative
    
#     # Path to the .keras model file (adjust the path as needed)
#     content_model_path = 'ContentBasedFilteringModel.keras'

#     collaborative_model_path = 'CollaborativeFilteringModel.keras'

    
#     try:
#         # Load the .keras model directly
#         content_model = tf.keras.models.load_model(content_model_path)
#         collaborative_model = tf.keras.models.load_model(collaborative_model_path)

        
#         # Assign the loaded model to the global variable
#         model_content = content_model
#         model_collaborative = collaborative_model
        
#         print("Content model loaded successfully")
    
#     except Exception as e:
#         print(f"Error loading content model: {e}")

# try:
#     load_models()
# except Exception as e:
#     print(f"Error loading models: {e}")
