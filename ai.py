import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import openai
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load configuration
with open('config.json') as config_file:
    config = json.load(config_file)

# Set up Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(config['google_sheets']['credentials_file'], scope)
client = gspread.authorize(creds)

# Set up OpenAI API
openai.api_key = os.getenv('OPENAI_API_KEY')

# Function to read article titles from Google Sheets

def read_article_titles(sheet_id, range_name):
    try:
        sheet = client.open_by_key(sheet_id)
        worksheet = sheet.worksheet(range_name)
        titles = worksheet.col_values(1)  # Column A
        locations_and_titles = [{"cell": f"A{i+1}", "title": title} for i, title in enumerate(titles)]
        print(f"Google Sheet Articles with Locations: {locations_and_titles}")
        return locations_and_titles
    except Exception as e:
        print(f"Error reading article titles: {e}")
        return []


# Function to select articles using OpenAI o3 model
def select_articles(titles, prompt):
    try:
        # Prepare the messages for the API request
        messages = [{"role": "system", "content": "You are a helpful assistant."}]
        
        # Include an explicit instruction to select the most relevant articles
        prompt = f"{prompt}\n\nPlease select the most relevant articles from the list below:\n" + "\n".join([f"{i+1}. {title}" for i, title in enumerate(titles)])

        messages.append({"role": "user", "content": prompt})

        # Call the OpenAI Chat API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Use the appropriate model
            messages=messages,
            max_tokens=150
        )
        
        # Get the assistant's response (which should be a list of article titles)
        selected_articles = response['choices'][0]['message']['content'].strip()
        
        # If it's a comma-separated list of article titles, split them
        selected_articles = [article.strip() for article in selected_articles.split(',')]
        
        # Filter out any empty or malformed articles
        selected_articles = [article for article in selected_articles if article]
        
        return selected_articles
    except Exception as e:
        print(f"Error selecting articles: {e}")
        return []


# Function to write selected articles to assignments.txt
def write_assignments(selected_articles):
    try:
        with open('assignments.txt', 'w') as file:
            for article in selected_articles:
                file.write(f"{article}\n")
    except Exception as e:
        print(f"Error writing assignments: {e}")

# Function to read full article content from Google Sheets
def read_article_content(sheet_id, cell_reference):
    try:
        sheet = client.open_by_key(sheet_id)
        worksheet = sheet.sheet1
        cell = worksheet.acell(cell_reference)
        return cell.value
    except Exception as e:
        print(f"Error reading article content: {e}")
        return ""

# Function to rewrite article using OpenAI o3 model
def rewrite_article(content, prompt_file):
    try:
        with open(prompt_file, 'r') as file:
            prompt = file.read()

        messages = [{"role": "system", "content": "You are a helpful assistant."}]
        messages.append({"role": "user", "content": prompt + "\n" + content})

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Or gpt-4 if needed
            messages=messages,
            max_tokens=500
        )
        
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Error rewriting article: {e}")
        return ""

# Function to generate image using GPT-4o
def generate_image(description):
    try:
        # Placeholder for GPT-4o API call
        return "image_url_placeholder"
    except Exception as e:
        print(f"Error generating image: {e}")
        return ""

# Function to upload articles to WordPress
def upload_to_wordpress(title, content, image_url):
    try:
        # Upload image to WordPress
        media_url = config['wordpress']['url'] + '/wp-json/wp/v2/media'
        media_data = {
            'file': image_url,
            'title': title,
            'alt_text': title
        }
        media_headers = {
            'Authorization': f"Basic {config['wordpress']['username']}:{config['wordpress']['password']}"
        }
        media_response = requests.post(media_url, files=media_data, headers=media_headers)
        if media_response.status_code == 201:
            media_id = media_response.json()['id']
            print(f"Image uploaded successfully with ID: {media_id}")
        else:
            print(f"Failed to upload image. Status code: {media_response.status_code}")
            return

        # Create post with image
        post_url = config['wordpress']['url'] + '/wp-json/wp/v2/posts'
        post_data = {
            'title': title,
            'content': content,
            'status': 'publish',
            'featured_media': media_id
        }
        post_response = requests.post(post_url, json=post_data, headers=media_headers)
        if post_response.status_code == 201:
            print(f"Article '{title}' uploaded successfully.")
        else:
            print(f"Failed to upload article '{title}'. Status code: {post_response.status_code}")
    except Exception as e:
        print(f"Error uploading to WordPress: {e}")

# Main function
def main():
    titles = read_article_titles(config['google_sheets']['sheet_id'], 'Sheet1')
    selected_articles = select_articles(titles, 'prompt.txt')

    # write to assignment.txt
    write_assignments(selected_articles)
    print(selected_articles)

    # Step 2: Article Writing
    # with open('assignments.txt', 'r') as file:
    #     assignments = file.readlines()

    # for assignment in assignments:
    #     content = read_article_content(config['google_sheets']['sheet_id'], assignment.strip())
        # rewritten_content = rewrite_article(content, 'prompt2.txt')
        # image_description = "Generated image description"  # Placeholder
        # image_url = generate_image(image_description)

        # # Step 4: WordPress Upload
        # upload_to_wordpress("Generated Title", rewritten_content, image_url)

        # # Remove processed assignment
        # assignments.remove(assignment)
        # with open('assignments.txt', 'w') as file:
        #     file.writelines(assignments)

if __name__ == "__main__":
    main()
