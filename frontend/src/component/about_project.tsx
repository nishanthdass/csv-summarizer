import React from 'react';

const agentSketch = require('../assets/CSV_Summarizer_4_20_25.pdf');

const AboutProject: React.FC = () => {
  return (
    <div className="about-project-container">
      <iframe src={agentSketch} width="100%" height="600px" title="Agent Sketch PDF" />
    </div>
  );
};


export default AboutProject;