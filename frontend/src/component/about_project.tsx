import React from 'react';

const AboutProject: React.FC = () => {
  return (
    <div className="about-project-container">
      <h2>About the Project</h2>
      
      <h3>Objective</h3>
      <p>
        This project aims to create a smart table powered by GPT and CrewAI that interacts with a user's SQL database. It uses autonomous agents to assist with:
      </p>
      <ul>
        <li>Query generation based on natural language input</li>
        <li>Column summarization and data insights</li>
        <li>Automated data analytics and trend analysis</li>
      </ul>
      
      <h3>Features</h3>
      <ul>
        <li>
          <strong>Interactive Query Generation Chatbot:</strong> A chatbot where users can ask questions in natural language about their data.
          <ul>
            <li>Handles questions such as "How many...", "Sum of...", "Most recent...", etc.</li>
            <li>Generates SQL queries to fetch or summarize information from the database.</li>
          </ul>
        </li>

        <li>
          <strong>Data Summarization of Table Selections:</strong> Summarizes selected columns, rows, or cells within the table.
          <ul>
            <li>Displays summaries based on user interaction (e.g., clicking, hovering).</li>
            <li>Leverages Query Generation and RAG (Retrieval-Augmented Generation) to provide context and insights.</li>
          </ul>
        </li>
        
        <li>
          <strong>Analytical Chatbot with Predictive Analysis:</strong> An analytic chatbot that uses Machine Learning and Agentic AI to analyze data patterns and trends.
          <ul>
            <li>Answers questions like "What is the best price for product XYZ?" or "What is a good price for XYZ?"</li>
            <li>Uses predictive models to perform trend analysis and forecasting.</li>
          </ul>
        </li>
      </ul>

      <h3>Agentic Approach</h3>
      <p>
        This project utilizes an agentic approach, with multiple autonomous agents working collaboratively:
      </p>
      <ul>
        <li>
          <strong>Query Generation Agent:</strong> Generates SQL queries based on user prompts and interactions. Works with other agents to retrieve relevant data for analysis and summarization.
        </li>
        <li>
          <strong>Analytics Agent:</strong> Performs data analysis and predictive modeling, responding to questions about data trends, pricing, and predictions.
        </li>
        <li>
          <strong>Summarization Agent:</strong> Summarizes selected data from the table, providing insights in tooltips or side panels based on user selections.
        </li>
        <li>
          <strong>Coordinator Agent:</strong> Manages communication and task allocation among agents, ensuring efficient data processing and interaction for the user.
        </li>
      </ul>
    </div>
  );
};

export default AboutProject;
