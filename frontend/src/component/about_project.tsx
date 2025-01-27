import React from 'react';

const AboutProject: React.FC = () => {
  return (
    <div className="about-project-container">
      <h2>About the Project</h2>
      
      <h3>Objective</h3>
      <p>
        This project aims to create an interactive smart table powered by a chatbot interface and multi-agent AI architecture. It enables SQL query generation, enriched insights from PDFs and CSVs, and automated data analytics to assist users in exploring, analyzing, and interpreting their data efficiently.
      </p>
      
      <h3>Features</h3>
      <p>
        This project introduces several advanced functionalities to enhance user interaction and data analysis.
      </p>
      <ul>
        
        <li>
          <strong>Interactive Query Generation:</strong> Users can ask questions in natural language about their data.
          
          <ul>
          <p>
            <li><span className='highlight-green'>Handles questions such as "How many...", "Sum of...", "Most recent...", etc.</span></li>
            <li><span className='highlight-green'>Automatically generates SQL queries to fetch or summarize information from the database, tailored to user inputs.</span></li>
            <li><span className='highlight-red'>Supports complex queries with conditions, aggregations, and joins.</span></li>
            <li><span className='highlight-yellow'>Utilizes queries to filter results in the table or highlight specific data using the ctid.</span></li>
          </p>
          </ul>
          
        </li>
        <li>
          <strong>Augmented Data Insights:</strong> Users can provide context related to CSV data by uploading supporting PDFs.
          <ul>
          <p>
            <li><span className='highlight-yellow'>Uses PDF data to generate insights for the user, supporting standalone Q&A retrievals and <span className='highlight-red'>image extractions from the PDF.</span></span></li>
            <li><span className='highlight-yellow'>Enhances retrievals by building knowledge graphs to form relationships between PDF(nodes such as chapters, pages, headers, lines) and CSV. PDF and CSV nodes are contextualized with semantic summaries and keywords.</span></li>
            <li><span className='highlight-yellow'>Clusters nodes from the PDF and CSV using natural language processing (NLP) to group related content by themes or topics. These clusters establish relationships between nodes from both sources, enabling contextual associations.</span></li>
            <li><span className='highlight-yellow'>Uses PDF data and contextual clusters to autocomplete cell content in newly added columns, leveraging relationships established in the knowledge graph.</span></li>
          </p>
          </ul>
        </li>
        <li>
          <strong>Data Analytics:</strong> Uses Machine Learning and Agentic AI to analyze data patterns and trends.
          
          <ul>
          <p> 
            <span className='highlight-red'>
            <li>Guides users through the data analytics process, helping them normalize, clean, and prepare data for modeling.</li>
            <li>Provides visualizations to aid user understanding and assist in selecting the right model for their use case.</li>
            <li>Runs predictive models and provides detailed metrics for evaluation.</li>
            </span>
          </p>
          </ul>

        </li>
      </ul>

      <h3>Agentic Approach</h3>
      <p>
        Behind the scenes, a multi-agent architecture powers these features, ensuring seamless collaboration between different components. This project utilizes agents (nodes) and conditions (edges) that make up a graph in Langgraph, with multiple agents working collaboratively:
      </p>
      <table border={1}>
        <thead>
          <tr>
            <th>Agent Name</th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>📝 <strong>SQL Agent</strong></td>
            <td>Automatically generates SQL queries based on user prompts and interactions, working with other agents to retrieve relevant data for analysis and summarization.</td>
          </tr>
          <tr>
            <td>📈 <strong>Analytics Agent</strong></td>
            <td>Conducts data analysis and predictive modeling, providing insights on trends, pricing, and predictions, while guiding users in model training and evaluation.</td>
          </tr>
          <tr>
            <td>📚 <strong>PDF Reader Agent</strong></td>
            <td>Interprets PDFs and enhances responses with context and insights. Supports Q&A and image retrieval tasks.</td>
          </tr>
          <tr>
            <td>🤖 <strong>Supervisor Agent</strong></td>
            <td>Manages communication and task allocation among agents, ensuring efficient data processing and interaction for the user.</td>
          </tr>
        </tbody>
      </table>

    </div>
  );
};

export default AboutProject;
