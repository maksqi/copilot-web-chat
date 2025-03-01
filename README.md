# Copilot Web Chat

A real-time AI chat application powered by GitHub Copilot's API, built with Flask and modern web technologies.

🌐 **Try it live at: [space123.space](https://space123.space/)**

![Chat Interface](https://i.imgur.com/EwWdvMv.png)

## Features

- 🤖 Real-time chat with advanced AI models (GPT-4, Claude 3.5 Sonnet, and more)
- 💬 Multiple chat sessions support
- 📝 Markdown formatting support
- 🎨 Code syntax highlighting
- 📋 One-click code copying
- 📱 Responsive design for mobile devices
- 🌙 Dark mode interface
- 🔄 Auto-generated chat titles
- 📊 Message statistics tracking

## Technologies Used

- Backend:
  - Python
  - Flask
  - SQLite
  - GitHub Copilot API
- Frontend:
  - HTML5
  - CSS3
  - JavaScript
  - Highlight.js
  - Marked.js
  - Font Awesome

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/maksqi/copilot-web-chat.git
   cd copilot-web-chat
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   - Create a `.env` file in the root directory
   - Add your GitHub Copilot API ghu_ key:
     ```
     COPILOT_TOKENS=token1,token2
     SECRET_KEY=random_string
     ```

5. Initialize the database:
   ```bash
   python init_db.py
   ```

6. Run the application:
   ```bash
   python app.py
   ```

7. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

## Features in Detail

### Chat Management
- Create new chat sessions
- Rename existing chats
- Delete chat sessions
- Switch between different chat contexts

### Message Handling
- Real-time message sending and receiving
- Markdown support for rich text formatting
- Code syntax highlighting with copy functionality
- Typing indicators
- Message history persistence

### AI Models
  - Claude 3.7 Sonnet (best model)
  - Claude 3.5 Sonnet
  - GPT-4
  - GPT-4o
  - o1
  - o3-mini
  - Gemini 2.0 Flash

### User Interface
- Clean, modern dark theme
- Responsive design for all devices
- Intuitive chat navigation
- Message statistics tracking
- Easy model switching

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

For questions or feedback, please reach out to [@maksqi](https://github.com/maksqi)