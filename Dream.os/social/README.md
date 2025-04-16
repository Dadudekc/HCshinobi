# Dream.OS Social Media Content Pipeline

Automated pipeline for transforming ChatGPT conversations into structured blog posts and social media content.

## Features

- Scrapes ChatGPT conversations and transforms them into structured content
- Generates blog posts with proper formatting and metadata
- Creates platform-specific social media posts (Twitter, LinkedIn)
- Analyzes optimal posting times based on engagement metrics
- Automatically schedules and dispatches content across platforms
- Tracks post performance and provides insights

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/dream-os-social.git
cd dream-os-social
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development
```

## Configuration

1. Copy the environment template:
```bash
cp .env.template .env
```

2. Configure the following in your `.env`:
- ChatGPT credentials
- Twitter API credentials
- LinkedIn API credentials
- Database settings
- Content directories

## Production Deployment

1. Set up directory structure:
```bash
mkdir -p content/{posts,social}
mkdir -p logs
```

2. Configure logging:
```bash
# In production.env
LOG_LEVEL=INFO
LOG_FILE=/path/to/logs/social_pipeline.log
```

3. Set up systemd service (Linux):
```ini
[Unit]
Description=Dream.OS Social Media Pipeline
After=network.target

[Service]
Type=simple
User=dreamos
WorkingDirectory=/path/to/dream-os-social
Environment=ENV=production
EnvironmentFile=/path/to/production.env
ExecStart=/path/to/venv/bin/python -m utils.devlog_generator
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

4. Enable and start the service:
```bash
sudo systemctl enable dreamos-social
sudo systemctl start dreamos-social
```

## Usage

### Manual Execution
```python
from utils.devlog_generator import DevLogGenerator
from utils.devlog_dispatcher import DevLogDispatcher

# Initialize components
generator = DevLogGenerator()
dispatcher = DevLogDispatcher(
    twitter_config=config,
    linkedin_config=config
)

# Process and publish content
chat_data = generator.scraper.scrape_latest()
generator.auto_publish(chat_data, dispatcher)
```

### Monitoring

1. Check service status:
```bash
sudo systemctl status dreamos-social
```

2. View logs:
```bash
tail -f /path/to/logs/social_pipeline.log
```

3. Monitor content directories:
```bash
ls -l content/posts/  # Blog posts
ls -l content/social/  # Social media content
```

## Testing

Run the test suite:
```bash
pytest tests/ -v --cov=utils --cov=strategies
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

Copyright © 2024 Dream.OS. All rights reserved. 