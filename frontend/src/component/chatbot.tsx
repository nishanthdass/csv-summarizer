import React, { useState } from 'react';

type ChatbotProps = {
    table: string | null;
};

const Chatbot: React.FC<ChatbotProps> = ({ table }) => {
    const [messages, setMessages] = useState<{ sender: string; text: string }[]>([]);
    const [input, setInput] = useState('');

    const sendMessage = async () => {
        if (input.trim() === '') return;

        // Append user's message to the chat window
        setMessages([...messages, { sender: 'User', text: input }]);

        try {
            const message = {
                question: input,
                table: table,
            }
            // Use fetch to send a POST request with the message in the body
            const response = await fetch('http://localhost:8000/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message }), // Send message in JSON format
            });

            const data = await response.json(); // Parse the JSON response
            console.log(data.response);
            // Append chatbot's response to the chat window
            setMessages(prevMessages => [...prevMessages, { sender: 'ChatBot', text: data.response }]);
        } catch (error) {
            console.error('Error communicating with the chat server:', error);
        }

        setInput('');
    };

    return (
    <>
        <div className="conversation-window">
            {messages.map((msg, index) => (
                <div key={index} className={`message ${msg.sender === 'User' ? 'user' : 'bot'}`}>
                    <strong>{msg.sender}:</strong> {msg.text}
                </div>
            ))}
        </div>
        <div className="input-container">
            <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type your message here..."
            />
            <button onClick={sendMessage}>Send</button>
        </div>
    </>
    );
};

export default Chatbot;
