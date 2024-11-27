import React, { useState, useEffect } from 'react';
import { useDataContext } from '../context/useDataContext';

type AnalysisTabProps = {
    table: string | null;
};

const AnalysisTab: React.FC<AnalysisTabProps> = ({ table }) => {
    const { tableConversation } = useDataContext();
    const [conversation, setConversation] = useState<string[]>([]);




    console.log(table)

    useEffect(() => {
        if (table && tableConversation[table]) {
          setConversation(tableConversation[table]);
        }
      }, [tableConversation, table]);
      



    
      return (
        <>
          <div className="conversation-window">
            {conversation.length > 0 ? (
              conversation.map((message, index) => (
                <div key={index} className="conversation-item">
                  {Object.entries(message).map(([key, value]) => (
                    <p key={key}>
                      <strong>{key}:</strong> {String(value)}
                    </p>
                  ))}
                </div>
              ))
            ) : (
              <div>No conversation yet</div>
            )}
          </div>
        </>
      );
      
      
};

export default AnalysisTab;
