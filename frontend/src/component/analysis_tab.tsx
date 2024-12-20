import React, { useEffect, useState } from 'react';
import { useDataContext } from '../context/useDataContext';
import { useTasks } from '../context/useTaskContext';
import { useChatWebSocket } from '../context/useChatWebsocket';
import ReactMarkdown from "react-markdown";

const AnalysisTab = () => {
const { currentTable } = useDataContext();
const { tasks } = useTasks();

const { isConnected, sendMessage, messages } = useChatWebSocket();
// const [messages, setMessages] = useState<Message[]>([]);
const [input, setInput] = useState('');
const [animatedDots, setAnimatedDots] = useState('');

const tasksForCurrentTable = tasks.filter(
    (task) => task.table_name === currentTable?.name
  );

const isLoading = tasksForCurrentTable.some(
    (task) => task.status !== 'Completed' && task.status !== 'Failed'
  );



const handleSend = () => {
    if (isConnected) {
        animate_dot();
        sendMessage(currentTable?.name || '', input);
        setInput('');
    }
};

const animate_dot = () => {
    const dots = ['.', '..', '...'];
    let index = 0;
    const interval = setInterval(() => {
        index = (index + 1) % 3;
        setAnimatedDots(dots[index]);
    }, 500);
    return () => clearInterval(interval);
};

return (
<>
    <div className="conversation-window">
    {isLoading ? (
        <p>Loading...</p>
    ) : (
        <>
        <div>
            <strong>Status:</strong> {isConnected ? "Connected" : "Disconnected"}
        </div>
        <div className="chat-messages">
            {messages.map((message, index) => (
            <span key={index} className="message-line">
                <strong>{message.role}:</strong>{" "}
                <ReactMarkdown
                components={{
                    p: ({ children }) => <span>{children}</span>, // Render paragraphs as spans
                }}
                >
                {message.message == "" ? animatedDots : message.message}
                </ReactMarkdown>
            </span>
            ))}
        </div>
        </>
    )}
    </div>

    <div className="input-container">
        <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message here..."
            onKeyDown={(e) => {
                if (e.key === 'Enter' && input.trim() !== '') {
                    handleSend(); // Call your message sending logic
                }
              }}
            autoFocus
        />
        <button onClick={handleSend}>Send</button>
    </div>
</>
);
};

export default AnalysisTab;

