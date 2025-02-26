import React, { useEffect, useState, useRef } from 'react';
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
const [collapsedStates, setCollapsedStates] = useState<Record<number, boolean>>({});

const tasksForCurrentTable = tasks.filter(
    (task) => task.name === currentTable?.name
  );

const isLoading = tasksForCurrentTable.some(
    (task) => task.status !== 'Completed' && task.status !== 'Failed'
  );

const scrollToBottomRef = useRef<HTMLDivElement>(null);

useEffect(() => {

    if (messages.length > 0) {
        const message = messages[messages.length - 1]
        scrollToBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
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
        sendMessage(currentTable?.name || '', '',input);
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

                typeof message.visualizing_query === 'string' && message.visualizing_query.length > 0  ? (
                    <span key={index} className={`message-line ${message.role}`}>
                    <strong>{message.role}:</strong>
                    
                    {message.message === "" ? (
                        animatedDots
                    ) : (
                    <span dangerouslySetInnerHTML={{ __html: message.message }} />
                    )}
                    
                    <p>
                    <button className="sql-query-button" onClick={() => message.visualizing_query && handleClickSql(message.visualizing_query, message.table_name)}>{message.viewing_query_label}</button>
                    </p>
                    
                    {message.role !== "User" && message.token_object && message.token_object.length > 0 && (
                    <>
                    <br/>
                    <br/>
                    <table className="token-table">
                        <thead>
                        <tr>
                            <th>Run ID</th>
                            <th>Model Name</th>
                            <th>Tool call</th>
                            <th>Input Tokens</th>
                            <th>Output Tokens</th>
                            <th>Total Tokens</th>
                        </tr>
                        </thead>
                        <tbody>
                        {message.token_object.map((token, i) => (
                            <tr key={i}>
                            <td>{token.run_id || "N/A"}</td>
                            <td>{token.model_name}</td>
                            <td>{token.tool_call_name}</td>
                            <td>{token.input_tokens}</td>
                            <td>{token.output_tokens}</td>
                            <td>{token.total_tokens}</td>
                            </tr>
                        ))}
                        </tbody>
                    </table>
                    </>
                    )}
                    <div className='chat-info'>
                    {message.role !== "User" && (
                        <>
                        <br/>
                        <div className='chat-thread-id'>Thread ID: {String(message.thread_id)}</div>
                        <div className='chat-time'>Response time: {String(message.time)} seconds</div>
                        </>
                        )}
                    </div>
                    </span>
                ) : (
                <span key={index} className={`message-line ${message.role}`} >
                <strong>{message.role}:</strong>
                
                {message.message === "" ? animatedDots : "  " + message.message}
            
                {message.role !== "User" && message.token_object && message.token_object.length > 0 && (
                    <>
                    <br/>
                    <br/>
                    <table className="token-table">
                        <thead>
                        <tr>
                            <th>Run ID</th>
                            <th>Model Name</th>
                            <th>Tool call</th>
                            <th>Input Tokens</th>
                            <th>Output Tokens</th>
                            <th>Total Tokens</th>
                        </tr>
                        </thead>
                        <tbody>
                        {message.token_object.map((token, i) => (
                            <tr key={i}>
                            <td>{token.run_id || "N/A"}</td>
                            <td>{token.model_name}</td>
                            <td>{token.tool_call_name}</td>
                            <td>{token.input_tokens}</td>
                            <td>{token.output_tokens}</td>
                            <td>{token.total_tokens}</td>
                            </tr>
                        ))}
                        </tbody>
                    </table>
                    </>
                    )}
                <div className='chat-info'>
                <br/>
                {message.role !== "User" && (
                    <>
                    <div className='chat-thread-id'>Thread ID: {String(message.thread_id)}</div>
                    <div className='chat-time'>Response time: {String(message.time)} seconds</div>
                    </>
                    )}
                </div>
                </span>
                )
            )}
            <div ref={scrollToBottomRef}></div>
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

