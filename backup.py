# # Function to save articles to Firebase
# def save_articles_to_firebase():
#     try:
#         # Open and read the CSV file
#         with open('articles_selected.csv', 'r', encoding='utf-8') as csv_file:
#             csv_reader = csv.DictReader(csv_file)
            
#             # Iterate over each row in the CSV file
#             for row in csv_reader:
#                 # Convert cited_by to integer
#                 row['cited_by'] = int(row['cited_by'])
                
#                 # Add empty list for rated_users
#                 row['rated_users'] = []
                
#                 # Save the article to the Firebase articles collection
#                 db.collection('articles').document(row['article_id']).set(row)
        
#         return "Articles saved to Firebase successfully."
    
#     except Exception as e:
#         return f"Error saving articles to Firebase: {e}"


# # Route to save articles to Firebase
# @app.route('/save', methods=['GET'])
# def save_articles():
#     return save_articles_to_firebase()