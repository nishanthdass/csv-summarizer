import React, { useEffect, useState } from 'react';
import { useDataContext } from '../context/useDataContext';
import { useTasks } from '../context/useTaskContext';
import { useChatWebSocket } from '../context/useChatWebsocket';
import { useFetchDataDatabase } from '../hooks/fetch_hooks/useFetchDataDatabase';
import { useTableSelection } from '../hooks/useTableSelection';

const ChatbotTab = () => {
const { currentTable } = useDataContext();
const { setCellViaCtid } = useTableSelection();
const { fetchSqlQueryFromMessage } = useFetchDataDatabase();
const { tasks } = useTasks();

const { isConnected, sendMessage, messages } = useChatWebSocket();
const [input, setInput] = useState('');
const [animatedDots, setAnimatedDots] = useState('');

const tasksForCurrentTable = tasks.filter(
    (task) => task.name === currentTable?.name
  );

const isLoading = tasksForCurrentTable.some(
    (task) => task.status !== 'Completed' && task.status !== 'Failed'
  );



useEffect(() => {
    // print last message
    if (messages.length > 0) {
        const message = messages[messages.length - 1]
        // console.log(message)
        if (message.role === 'sql_agent') {
            console.log(message)
        }
    }
}, [messages]);

const handleShowOnly = async(message: string, table_name: string) => {
    if (isConnected) {
        try {
            console.log(message)
            const ctid = await fetchSqlQueryFromMessage(message, table_name);
            setCellViaCtid(ctid);
            
            
        } catch (error) {
            console.error(error);
        }
    }
};

const handleShowAndFilter = async (message: string, table_name: string) => {
    if (isConnected) {
        try {
            await fetchSqlQueryFromMessage(message, table_name);
        } catch (error) {
            console.error(error);
        }
    }
};


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
            {messages.map((message, index) => 
                message.is_action ? (
                    <span key={index} className={`message-line ${message.role}`} >
                    <strong>{message.role}:</strong>
                    {message.message === "" ? animatedDots : "  " + message.message}
                    <p>
                        <button className="sql-Query-button" onClick={() => handleShowOnly(message.message, message.table_name)}>Generate CTID via LLM</button>
                        <button className="sql-Query-button" onClick={() => handleShowAndFilter(message.message, message.table_name)}>Run SQL Query</button>
                    </p>
                    </span>
                ) : (
                <span key={index} className={`message-line ${message.role}`} >
                <strong>{message.role}:</strong>
                {message.message === "" ? animatedDots : "  " + message.message}
                </span>
                )
            )}
        </div>
        </>
    )}
    </div>

    <div className="input-container">
        <input
            type="text"
            disabled={!isConnected}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message here..."
            onKeyDown={(e) => {
                if (e.key === 'Enter' && input.trim() !== '') {
                    handleSend();
                }
              }}
            autoFocus
        />
        <button onClick={handleSend} disabled={!isConnected}>Send</button>
    </div>
</>
);
};

export default ChatbotTab;

