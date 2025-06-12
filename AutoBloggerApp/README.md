# AutoBloggerApp

An AI-powered blog generation and management system with WordPress integration.

## Project Structure

```
AutoBloggerApp/
├── autoblogger/                 # Main application package
│   ├── config/                  # Configuration files
│   │   ├── config.ini          # Main configuration
│   │   └── .env                # Environment variables
│   ├── services/               # Core business logic
│   │   ├── blog_generator.py   # Blog content generation
│   │   ├── vector_db.py        # Vector database for similarity search
│   │   └── wordpress_client.py # WordPress integration
│   ├── ui/                     # User interface
│   │   ├── main_window.py      # Main application window
│   │   └── dialogs.py          # Dialog windows
│   ├── worker/                 # Background processing
│   │   └── worker_thread.py    # Worker thread implementation
│   ├── utils/                  # Utilities
│   │   └── logging_setup.py    # Logging configuration
│   ├── models/                 # Data models
│   │   └── blog_post.py        # Blog post model
│   ├── templates/              # HTML templates
│   ├── resources/              # Static resources
│   └── output/                 # Generated content
├── scrapers/                   # Social media scrapers
│   ├── linkedin/               # LinkedIn scraping
│   │   ├── scraper.py         # LinkedIn scraper
│   │   └── processor.py       # Data processing
│   └── twitter/                # Twitter scraping
│       ├── scraper.py         # Twitter scraper
│       └── processor.py       # Data processing
├── training/                   # AI training code
│   ├── deepseek/              # DeepSeek model training
│   │   ├── train.py          # Training script
│   │   └── preprocess.py     # Data preprocessing
│   └── reply_ai/              # Reply AI training
│       ├── train.py          # Training script
│       └── preprocess.py     # Data preprocessing
├── tests/                      # Test suite
├── docs/                       # Documentation
├── data/                       # Data files
│   ├── raw/                    # Raw data
│   └── processed/              # Processed data
├── logs/                       # Log files
├── requirements.txt            # Dependencies
├── setup.py                    # Package setup
└── LICENSE                     # License file
```

## Features

- AI-powered blog content generation
- WordPress integration
- Vector database for similarity search
- Social media content scraping
- Custom AI model training
- User-friendly GUI interface
- Background processing
- Comprehensive logging
- Configuration management

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure WordPress settings:
- Copy `autoblogger/config/config.ini.example` to `autoblogger/config/config.ini`
- Update WordPress credentials and settings

3. Set up environment variables:
- Copy `.env.example` to `.env`
- Update API keys and sensitive information

4. Run the application:
```bash
python -m autoblogger.main
```

## Development

### Running Tests
```bash
python -m pytest
```

### Training Models
```bash
# Train DeepSeek model
python -m training.deepseek.train

# Train Reply AI model
python -m training.reply_ai.train
```

### Scraping Content
```bash
# LinkedIn scraping
python -m scrapers.linkedin.scraper

# Twitter scraping
python -m scrapers.twitter.scraper
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenAI for GPT integration
- WordPress REST API
- Twitter API
- LinkedIn API

## Support

For support, please open an issue in the GitHub repository or contact the maintainers.

## Roadmap

- [ ] Enhanced AI content generation
- [ ] Additional platform integrations
- [ ] Advanced analytics dashboard
- [ ] Content calendar management
- [ ] Automated image generation
- [ ] Multi-language support 