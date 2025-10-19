# Lingolino Refactored Structure

This directory contains the refactored version of the Lingolino prototype, with code organized into separate modules for better maintainability.

## File Structure

### Python Modules

- **`states.py`**: Contains state definitions
  - `State`: Main state for immediate response graph
  - `BackgroundState`: State for background analysis graph

- **`data_loaders.py`**: Data loading functions
  - `get_game_by_id()`: Retrieves game descriptions
  - `get_child_profile()`: Retrieves child profiles

- **`nodes.py`**: Node functions used in both graphs
  - `masterChatbot()`: Main chatbot that responds to children
  - `educationalWorker()`: Analyzes educational aspects
  - `storytellingWorker()`: Analyzes storytelling aspects
  - `format_response()`: Formats responses for TTS
  - `initialStateLoader()`: Loads initial state data
  - `load_analysis()`: Loads analysis from background graph
  - Helper functions for conditional edges

- **`immediate_graph.py`**: Immediate response graph
  - `create_immediate_response_graph()`: Creates the graph for real-time responses

- **`background_graph.py`**: Background analysis graph
  - `create_background_analysis_graph()`: Creates the graph for async analysis

### Notebooks

- **`lingolino_refactored.ipynb`**: New notebook that imports the modules above
- **`lingolino_prototype.ipynb`**: Original prototype (unchanged)

## Usage

Open `lingolino_refactored.ipynb` and run the cells in order:

1. Import modules
2. Load environment variables
3. Initialize LLM and memory
4. Create both graphs
5. Visualize the graphs
6. Run simulations or interactive chat

## Benefits of Refactoring

1. **Separation of Concerns**: Each file has a clear responsibility
2. **Reusability**: Functions can be imported and reused elsewhere
3. **Testability**: Individual modules can be tested independently
4. **Maintainability**: Easier to locate and modify specific functionality
5. **Original Preserved**: The original prototype remains untouched

## Graph Architecture

- **Immediate Response Graph**: Handles real-time user interactions
- **Background Analysis Graph**: Analyzes conversations asynchronously for educational and storytelling insights

