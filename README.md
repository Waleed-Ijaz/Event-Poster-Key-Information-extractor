# 📢 Event Poster Information Extractor

A powerful tool that automatically extracts key information from event posters using OCR technology and intelligent pattern recognition. Built with DocTR for optical character recognition and Gradio for an intuitive web interface.

## 🚀 Features

- **Automatic Text Extraction**: Uses DocTR (Document Text Recognition) for accurate OCR
- **Smart Information Parsing**: Extracts key details using specialized regex patterns
- **Multiple Output Formats**: Results available in JSON and CSV formats
- **User-Friendly Interface**: Clean Gradio web interface for easy interaction
- **Comprehensive Data Extraction**: Identifies event name, date, time, venue, contact details, pricing, and more

## 📋 Extracted Information

The system automatically identifies and extracts:

- **Event Name**: Main event title
- **Date**: Event date in various formats
- **Time**: Event timing and duration
- **Venue**: Location and address information
- **Target Audience**: Profession or demographic information
- **Event Type**: Online/Offline classification
- **Contact Information**: Phone numbers and email addresses
- **Social Media**: Links and handles
- **Pricing**: Ticket prices or free events

## 🛠️ Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/event-poster-extractor.git
cd event-poster-extractor
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the application**
```bash
python app.py
```

4. **Access the interface**
   - Open your web browser and navigate to `http://localhost:7860`
   - Upload an event poster image
   - Click "Extract Information" to get results

## 🎯 Usage

1. **Upload Image**: Select and upload your event poster image
2. **Extract Information**: Click the extract button to process the image
3. **View Results**: Check the extracted information in three tabs:
   - **Extracted Text**: Raw OCR output
   - **JSON Output**: Structured data in JSON format
   - **CSV Output**: Tabular data format

## 📁 Project Structure

```
event-poster-extractor/
├── app.py                 # Main application file
├── requirements.txt       # Python dependencies
├── README.md             # Project documentation
├── .gitignore           # Git ignore rules
└── examples/            # Sample poster images (optional)
```

## 🔧 Technical Details

### OCR Technology
- **DocTR**: State-of-the-art document text recognition
- **Preprocessing**: Automatic image optimization for better OCR accuracy

### Pattern Recognition
- **Regex Patterns**: Specialized patterns for different information types
- **Text Cleaning**: Normalization and cleanup of extracted text
- **Smart Matching**: Context-aware information extraction

### Supported Formats
- **Input**: JPG, PNG, GIF, BMP image formats
- **Output**: JSON, CSV data formats

## 💡 Tips for Best Results

- Use **high-resolution** poster images
- Ensure good **contrast** between text and background
- Make sure key information is **clearly visible**
- Avoid images with heavy distortion or rotation

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [DocTR](https://github.com/mindee/doctr) for excellent OCR capabilities
- [Gradio](https://gradio.app/) for the intuitive web interface
- The open-source community for various Python libraries used

## 📞 Support

If you encounter any issues or have questions, please:
1. Check the [Issues](https://github.com/yourusername/event-poster-extractor/issues) section
2. Create a new issue if your problem isn't already reported
3. Provide detailed information about your problem

## 🔮 Future Enhancements

- [ ] Support for multiple languages
- [ ] Batch processing of multiple images
- [ ] Integration with calendar applications
- [ ] Advanced image preprocessing options
- [ ] Export to additional formats (Excel, PDF)
- [ ] API endpoint for programmatic access

---

⭐ **Star this repository if you find it useful!**