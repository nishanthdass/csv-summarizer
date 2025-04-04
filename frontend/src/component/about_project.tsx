import React from 'react';
import agentSketch from '../assets/agent-sketch.png';

const AboutProject: React.FC = () => {
  return (
    <div className="about-project-container">
      <h2>About the Project</h2>
      
      <h3>Objective</h3>
      <p>
        This project aims to create an interactive smart table powered by a chatbot interface and multi-agent AI architecture. It enables SQL query generation, enriched insights by combining information from PDFs, and automated table manipulation to assist users in exploring and interpreting their data efficiently.
      </p>
      
      <h3>Features</h3>
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
            <li><span className='highlight-yellow'>Agents pass infromation between PDF and CSV to generate insights for the user, supporting standalone Q&A retrievals and <span className='highlight-red'>image extractions from the PDF.</span></span></li>
            <li><span className='highlight-yellow'>Enhances retrievals by building knowledge graphs to form relationships between PDF(nodes such as chapters, pages, headers, lines) and CSV. PDF and CSV nodes are contextualized with semantic summaries and keywords.</span></li>
            <li><span className='highlight-yellow'>Clusters nodes from the PDF and CSV using natural language processing (NLP) to group related content by themes or topics. These clusters establish relationships between nodes from both sources, enabling contextual associations.</span></li>
            <li><span className='highlight-yellow'>Uses PDF data and contextual clusters to autocomplete cell content in newly added columns, leveraging relationships established in the knowledge graph.</span></li>
          </p>
          </ul>
        </li>
      </ul>

      <h3>Agentic Approach</h3>
      <p>
        Behind the scenes, a multi-agent architecture powers these features, ensuring seamless collaboration between different components. This project utilizes agents (nodes) and conditions (edges) that make up a graph in Langgraph, with multiple agents working collaboratively:
      </p>
      <img src={agentSketch} alt="Agent Sketch" className='agent-sketch-img'/>
      <table border={1}>
        <thead>
          <tr>
            <th>Agent Name</th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>🤖 <strong>Supervisor Agent</strong></td>
            <td>Manages communication and task allocation among agents, ensuring efficient data processing and interaction for the user.</td>
          </tr>
          <tr>
            <td>📝 <strong>SQL Agent</strong></td>
            <td>Automatically generates SQL queries based on user prompts and interactions, working with other agents to retrieve relevant data for analysis and summarization.</td>
          </tr>
          <tr>
            <td>📈 <strong>Data Analytics Agent</strong></td>
            <td>Conducts data analysis and predictive modeling, providing insights on trends, pricing, and predictions, while guiding users in model training and evaluation.</td>
          </tr>
          <tr>
            <td>📚 <strong>PDF Agent</strong></td>
            <td>Interprets PDFs and enhances responses with context and insights. Supports Q&A and image retrieval tasks.</td>
          </tr>
        </tbody>
      </table>

    </div>
  );
};

export default AboutProject;
