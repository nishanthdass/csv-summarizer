import React, { useEffect, useState, Fragment } from 'react';
import { useDataContext } from '../context/useDataContext';
import { useTasks } from '../context/useTaskContext';
import { useChatWebSocket } from '../context/useChatWebsocket';
import { useFetchDataDatabase } from '../hooks/fetch_hooks/useFetchDataDatabase';
import { useTableSelection } from '../hooks/useTableSelection';


const ChatbotTab = () => {
const { handleSqlQuerySelections } = useTableSelection();
const { currentTable } = useDataContext();

const { fetchRunSQLQuery } = useFetchDataDatabase();
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
    }
}, [messages]);

const handleClickSql = async(message: string, table_name: string) => {
    if (isConnected) {
        try {
            const response = await fetchRunSQLQuery(message, table_name);
            handleSqlQuerySelections?.(response.data);
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
                
                typeof message.modified_query === 'string' && message.modified_query.length > 0  ? (
                    <span key={index} className={`message-line ${message.role}`} >
                    <strong>{message.role}:</strong>
                    
                    {message.message === "" ? (
                        animatedDots
                    ) : (
                        <span dangerouslySetInnerHTML={{ __html: message.message }} />
                    )}
                    
                    <p>
                    <button className="sql-query-button" onClick={() => message.modified_query && handleClickSql(message.modified_query, message.table_name)}>{message.modified_query_label}</button>
                    </p>
                    <br/>
                    <br/>
                    {message.role === "User" ?(""): (<div className='chat-time'>Response time: {String(message.time)} seconds</div>)}
                    </span>
                ) : (
                <span key={index} className={`message-line ${message.role}`} >
                <strong>{message.role}:</strong>
                
                {message.message === "" ? animatedDots : "  " + message.message}
                <br/>
                <br/>
                {message.role === "User" ?(""): (<div className='chat-time'>Response time: {String(message.time)} seconds</div>)}
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

