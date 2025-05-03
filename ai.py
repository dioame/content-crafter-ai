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
def select_articles(titles_with_cells, prompt):
    try:
        # Create a simple list of titles to send to the LLM
        plain_titles = [item["title"] for item in titles_with_cells]

        # Prepare messages
        messages = [{"role": "system", "content": "You are a helpful assistant."}]
        full_prompt = f"{prompt}\n\nPlease select the most relevant articles from the list below:\n" + \
                      "\n".join([f"{i+1}. {title}" for i, title in enumerate(plain_titles)])
        messages.append({"role": "user", "content": full_prompt})

        # Call the OpenAI Chat API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=200
        )

        # Get and clean the assistant's response
        content = response['choices'][0]['message']['content'].strip()

        # Try to extract titles from numbered or bulleted list
        lines = content.split('\n')
        selected_titles = []
        for line in lines:
            # Handle lines like "1. Article Title" or "- Article Title"
            parts = line.split('. ', 1)
            if len(parts) == 2:
                selected_titles.append(parts[1].strip())
            else:
                # Fallback if no numbering
                line = line.lstrip("-•").strip()
                if line:
                    selected_titles.append(line)

        # Match back to original titles with cells
        selected_with_cells = []
        for title in selected_titles:
            match = next((item for item in titles_with_cells if item["title"].strip().lower() == title.lower()), None)
            if match:
                selected_with_cells.append(match)

        return selected_with_cells
    except Exception as e:
        print(f"Error selecting articles: {e}")
        return []



# Function to write selected articles to assignments.txt
def write_assignments(selected_articles):
    try:
        with open('assignments.txt', 'w') as file:
            for article in selected_articles:
                cell = article.get("cell", "")

                #in case we add the content next update
                # title = article.get("title", "")
                file.write(f"{cell}\n")
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




# Function to read content from specific Google Sheets cells
def get_article_content(sheet_id, cells):
    try:
        print(f"Processing: {cells}")  # Print out the cells to check if it's correct
        
        # Open the Google Sheet using the sheet ID
        sheet = client.open_by_key(sheet_id)

        # Open the first worksheet (you can modify to select another if needed)
        worksheet = sheet.get_worksheet(0)

        # Fetch content from the specified cells
        content = []
        
        if not isinstance(cells, list):
            print("Error: 'cells' parameter should be a list of cell references.")
            return []
        
        for cell in cells:
            # Check if cell is a valid string like 'A1', 'B2', etc.
            if not isinstance(cell, str):
                print(f"Error: Invalid cell reference {cell}, expected a string like 'A1'.")
                continue
            
            # Fetch the cell content
            cell_content = worksheet.acell(cell).value  # Get the value of the cell
     
        # Return the content of the specified cells
        return cell_content

    except Exception as e:
        print(f"Error reading content from Google Sheets: {e}")
        return []




# Function to rewrite the article using OpenAI's API
def rewrite_article(sheet_id, cells, prompt_file):
    print("--rewrite_article function--")
    
    # try:
    #     # Get content from the specified cells
    #     content = get_article_content(sheet_id, cells)
        
    #     # If content is empty, return an empty string
    #     if not content:
    #         return ""
        
    #     # Read the prompt from the file
    #     with open(prompt_file, 'r') as file:
    #         prompt = file.read().strip()

    #     # Combine the prompt and article content
    #     full_prompt = f"{prompt}\n\nContent:\n" + "\n".join(content)
        
    #     # Prepare the messages for the OpenAI API
    #     messages = [{"role": "system", "content": "You are a helpful assistant."}]
    #     messages.append({"role": "user", "content": full_prompt})

    #     # Make the API call to rewrite the article
    #     response = openai.ChatCompletion.create(
    #         model="gpt-3.5-turbo",  # You can use "gpt-4" for higher quality if needed
    #         messages=messages,
    #         max_tokens=500
    #     )
        
    #     # Get the rewritten content from the response
    #     rewritten_content = response['choices'][0]['message']['content'].strip()
        
    #     # Write the rewritten content back to the prompt file
    #     with open(prompt_file, 'w') as file:
    #         file.write(rewritten_content)
        
    #     return rewritten_content
    # except Exception as e:
    #     print(f"Error rewriting article: {e}")
    #     return ""


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


def clean_assignments(assignments):
    print(f"RAW Assignment: {assignments}")
    # Strip the newlines and extra spaces, and wrap each cell reference in a list
    cleaned_assignments = [[assignment.strip()] for assignment in assignments]
    return cleaned_assignments


def write_content(content, filename):
    try:
        # Ensure content ends with a newline for separation
        if not content.endswith("\n"):
            content += "\n"
        
        # Check if the file exists
        if os.path.exists(filename):
            # Append if the file exists
            with open(filename, 'a') as file:
                file.write(content)
            print(f"Content successfully appended to {filename}")
        else:
            # Write if the file does not exist
            with open(filename, 'w') as file:
                file.write(content)
            print(f"Content successfully written to {filename}")
    except Exception as e:
        print(f"Error writing content to file: {e}")


# Main function
def main():

    # print(f"config: sheetID [{config['google_sheets']['sheet_id']}]")

    # # Read titles from the sheet
    # titles = read_article_titles(config['google_sheets']['sheet_id'], 'Sheet1')
    # selected_articles = select_articles(titles, 'prompt.txt')

    selected_articles = [{'cell': 'A2', 'title': 'How to improve SEO for websites'}, {'cell': 'A4', 'title': 'Understanding Python decorators'}]

    # Write selected articles to assignments.txt
    write_assignments(selected_articles)
   
    print("--selected_articles--")
    print(selected_articles)


    # Step 2: Article Writing
    with open('assignments.txt', 'r') as file:
        assignments = file.readlines()

    print("--iterate assignment--")
    assignments = clean_assignments(assignments)
    print(assignments)
    
    for assignment in assignments:
        content = get_article_content(config['google_sheets']['sheet_id'],assignment)
        write_content(content, "prompt2.txt")
        
    #     # Output assignment details


    #     # Rewrite the article using OpenAI with the prompt from prompt2.txt
    #     rewritten_content = rewrite_article(config['google_sheets']['sheet_id'], [assignment['cell']], 'prompt2.txt')
        
    #     # Output the rewritten content for further use (e.g., uploading, saving, etc.)
    #     print(f"Rewritten Article for:\n{rewritten_content}\n")

    #     # image_description = "Generated image description"  # Placeholder
    #     # image_url = generate_image(image_description)

    #     # # Step 4: WordPress Upload
    #     # upload_to_wordpress("Generated Title", rewritten_content, image_url)

    #     # # Remove processed assignment
    #     # assignments.remove(assignment)
    #     # with open('assignments.txt', 'w') as file:
    #     #     file.writelines(assignments)

if __name__ == "__main__":
    main()
