import React, { useEffect, useState, useRef } from 'react';
import { useDataContext } from '../context/useDataContext';
import { useTasks } from '../context/useTaskContext';
import { useChatWebSocket } from '../context/useChatWebsocket';
import { useFetchDataDatabase } from '../hooks/fetch_hooks/useFetchDataDatabase';
import { useTableSelection } from '../hooks/useTableSelection';
import { useFileSidePanelOperations } from '../hooks/useFileSidePanelOperations';



const ChatbotTab = () => {


const { handleSqlQuerySelections } = useTableSelection();
const { loadTableFromDatabase} = useFileSidePanelOperations();
const { currentTable, currentPdf } = useDataContext();

const { fetchRunSQLQuery } = useFetchDataDatabase();
const { tasks } = useTasks();

const { isConnected, sendMessage, messages } = useChatWebSocket();
const [input, setInput] = useState('');
const [animatedDots, setAnimatedDots] = useState('');
const [collapsedStates, setCollapsedStates] = useState<Record<number, boolean>>({});


const groupedMessages = messages.reduce((acc, message) => {
    const lastGroup = acc[acc.length - 1];

    if (lastGroup && lastGroup.role === message.role) {
        // Append message to the last group
        lastGroup.messages.push(message.message);
        lastGroup.token_objects = lastGroup.token_objects.concat(message.token_object || []);
    } else {
        // Create a new group
        acc.push({ role: message.role, messages: [message.message], token_objects: message.token_object || [] });
    }

    return acc;
}, [] as { role: string; messages: string[]; token_objects: any[] }[]);



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
    // console.log("Last message changed:", messages[messages.length - 1]);
}, [messages]);

const handleClickSql = async(message: string, table_name: string, role: string, query_type: string) => {
    if (isConnected) {
        console.log("Click SQL: ", message);
        try {
            const response = await fetchRunSQLQuery(message, table_name, role, query_type);
            loadTableFromDatabase(table_name);
            handleSqlQuerySelections?.(response.data);
        } catch (error) {
            console.error(error);
        }
    }
};


const handleSend = () => {
    if (isConnected) {
        animate_dot();
        sendMessage(currentTable?.name || '', currentPdf?.name || '',input);
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
        {groupedMessages.map((group, index) => (
            <div key={index} className={`message-line ${group.role}`}>
                <strong>{group.role}:</strong>
                <div>
                    {group.messages.map((msg, i) => (
                        <p key={i} dangerouslySetInnerHTML={{ __html: msg }} />
                    ))}
                </div>

                {group.role !== "User" && group.token_objects.length > 0 && (
                    <>
                        <br />
                        <br />
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
                                {group.token_objects.map((token, i) => (
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
            </div>
        ))}
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

