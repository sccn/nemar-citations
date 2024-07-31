# %%
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx

# Load the dataset citations analysis CSV file
df_analysis = pd.read_csv('citations/dataset_citations_analysis.csv')

# %% Create a directed graph

# Create a directed graph
G = nx.DiGraph()

# Add nodes and edges for each dataset
for i, row in df_analysis.iterrows():
    dataset = row['Dataset']
    num_citations = row['Number of Citations']
    cum_citations = row['Cumulative Citations to Papers']
    
    # Add the dataset node
    G.add_node(dataset, size=num_citations * 100, color='blue')
    
    # Add a node for the cumulative citations stemming from the dataset
    G.add_node(f"{dataset}_cum", size=cum_citations * 10, color='green')
    
    # Add an edge from the dataset to the cumulative citations node
    G.add_edge(dataset, f"{dataset}_cum")

# Identify the top 20 datasets with the highest number of citations
top_20_datasets = df_analysis.nlargest(20, 'Number of Citations')['Dataset']

# Simplify names only for the top 20 datasets
simplified_names = {node: (node if node in top_20_datasets.values else '') for node in G.nodes}

# Define new colors for better engagement
engaging_colors = {'blue': '#87CEEB', 'green': '#98FB98'}

# Adjust the spring layout parameters for better distribution
pos = nx.spring_layout(G, k=0.1, iterations=100)

# Draw the tree graph with updated labels and colors
plt.figure(figsize=(14, 10))
nx.draw(G, pos, labels=simplified_names, node_size=[G.nodes[node]['size'] for node in G.nodes], 
        node_color=[engaging_colors['blue'] if 'cum' not in node else engaging_colors['green'] for node in G.nodes], 
        font_size=10, font_weight='bold', edge_color='gray')

# Add labels to indicate the meaning of the colors
blue_patch = plt.Line2D([0], [0], marker='o', color='w', label='Number of Citations', markersize=10, markerfacecolor=engaging_colors['blue'])
green_patch = plt.Line2D([0], [0], marker='o', color='w', label='Cumulative Citations to Papers', markersize=10, markerfacecolor=engaging_colors['green'])
plt.legend(handles=[blue_patch, green_patch], loc='best')

# Show the plot
plt.title('Tree Graph of Dataset Citations and Cumulative Citations to Papers')
plt.show()



# bar and line chart
# Create a combined bar and line chart for clearer visualization
fig, ax1 = plt.subplots(figsize=(14, 8))

# Bar chart for Number of Citations
color = 'tab:blue'
ax1.set_xlabel('Dataset')
ax1.set_ylabel('Number of Citations', color=color)
ax1.bar(df_analysis['Dataset'], df_analysis['Number of Citations'], color=color, alpha=0.6, label='Number of Citations', log=True)
ax1.tick_params(axis='y', labelcolor=color)
ax1.set_xticklabels(df_analysis['Dataset'], rotation=90)

# Line chart for Cumulative Citations to Papers
ax2 = ax1.twinx()
color = 'tab:green'
ax2.set_ylabel('Cumulative Citations to Papers', color=color)
ax2.plot(df_analysis['Dataset'], df_analysis['Cumulative Citations to Papers'], color=color, marker='o', linestyle='-', linewidth=2, markersize=6, label='Cumulative Citations to Papers')
ax2.tick_params(axis='y', labelcolor=color)

# Add title and legend
plt.title('Number of Citations and Cumulative Citations to Papers for Each Dataset')
fig.tight_layout()
fig.legend(loc='upper right', bbox_to_anchor=(0.85, 0.85))

# Show the plot
plt.show()

# %%
