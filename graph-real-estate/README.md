# Real Estate Graph Builder

A modular Neo4j graph database application for real estate data with Pydantic validation.

## 🏗️ Architecture

This application follows a **clean, modular architecture** designed for maintainability and growth:

```
graph-real-estate/
├── src/                    # Source code (modular organization)
│   ├── models/            # Pydantic data models
│   │   ├── property.py    # Property-related models
│   │   ├── graph.py       # Graph node models
│   │   └── relationships.py # Relationship models
│   ├── data/              # Data loading and processing
│   │   └── loader.py      # JSON data loader with validation
│   ├── database/          # Database layer
│   │   └── neo4j_client.py # Neo4j connection and utilities
│   └── controllers/       # Business logic
│       └── graph_builder.py # Main graph building logic
├── config/                # Configuration
│   └── settings.py        # Application settings
├── main.py               # Entry point
├── requirements.txt      # Dependencies
├── .env                  # Environment variables
└── README.md            # This file
```

## 🚀 Features

- **Pydantic Validation**: All data structures validated with Pydantic models
- **Modular Design**: Clean separation of concerns for easy maintenance
- **Type Safety**: Full type hints throughout the codebase
- **Scalable Architecture**: Ready for future enhancements
- **Neo4j Community Edition**: Uses free version of Neo4j

## 📊 Data Model

The graph consists of:
- **84 Properties** (44 San Francisco, 40 Park City)
- **387 Features** organized in 8 categories
- **21 Neighborhoods** across 2 cities
- **1,267 Relationships** connecting the data

## 🔧 Installation

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Start Neo4j** (Docker)
```bash
docker-compose up -d
```

3. **Configure Environment**
Edit `.env` file with your Neo4j credentials

## 🎮 Usage

```bash
# Run all phases
python main.py all

# Run individual phases
python main.py phase1    # Environment setup
python main.py phase2    # Build schema
python main.py phase3    # Create relationships

# Utilities
python main.py queries   # Run sample queries
python main.py stats     # View statistics
python main.py clear     # Clear database
```

## 📈 Sample Queries

After building the graph, you can run queries to explore:
- Properties by city
- Most expensive neighborhoods
- Feature distribution
- Similar properties
- Price ranges

## 🏛️ Why Modular Architecture?

### Benefits:
1. **Separation of Concerns**: Each module has a single responsibility
2. **Testability**: Easy to unit test individual components
3. **Maintainability**: Changes in one module don't affect others
4. **Scalability**: Easy to add new features or data sources
5. **Reusability**: Components can be reused in other projects

### Module Responsibilities:

- **models/**: Data validation and type definitions
- **data/**: Data loading and transformation logic
- **database/**: Database operations and connection management
- **controllers/**: Business logic and orchestration
- **config/**: Centralized configuration management

## 🔄 Future Enhancements

The modular structure makes it easy to add:
- Additional data sources
- New relationship types
- Advanced analytics
- API endpoints
- Caching layers
- Testing suites

## 📝 License

MIT