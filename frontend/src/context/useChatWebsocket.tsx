import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import { useFetchDataDatabase } from "../hooks/fetch_hooks/useFetchDataDatabase";


interface MessageInstance {
  role: string;
  table_name: string;
  event: string;
  message: string;
  modified_query?: string | null;
  modified_query_label?: string | null;
}

interface Message {
  role: string;
  sql_queries?: string
  table_name: string;
  run_id?: string;
  full_message: string;
}

interface ChatWebsocketContextValue {
  isConnected: boolean;
  sendMessage: (table_name: string, input: string) => void;
  input: MessageInstance[];
  messages: MessageInstance[];
  setMessages: React.Dispatch<React.SetStateAction<MessageInstance[]>>;
  reconnect: () => void;
  setIsChatOpen: React.Dispatch<React.SetStateAction<boolean>>
  isChatOpen: boolean
}

interface ChatWebsocketProviderProps {
  url: string;
  children: React.ReactNode;
}

const ChatWebsocketContext = createContext<ChatWebsocketContextValue | undefined>(undefined);

export const ChatWebsocketProvider: React.FC<ChatWebsocketProviderProps> = ({ url, children }) => {
  const [ isConnected, setIsConnected ] = useState(false);
  const [ isChatOpen, setIsChatOpen ] = useState(false);
  const [ messages, setMessages ] = useState<MessageInstance[]>([]);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectSocketRef = useRef(true);

  const { fetchStartChat } = useFetchDataDatabase();


  const formatIncomingMessage = (data: any): MessageInstance => {
    return {
      role: String(data.role),
      table_name: String(data.table_name),
      event: String(data.event),
      message: String(data.message),
      modified_query: String(data.modified_query),
      modified_query_label: String(data.modified_query_label),
    };
  };

  const formatOutgoingMessage = (role: string, table_name: string, message: string, event: string): MessageInstance => ({
    role,
    table_name,
    event,
    message,
  });


  // Socket operations
  const connect = () => {
    const socket = new WebSocket(url);
    socketRef.current = socket;

    socket.onopen = () => {
      // console.log("WebSocket connected");
      setIsConnected(true);
    };

    socket.onmessage = (event) => {
      try {
        const parsedData = JSON.parse(event.data);
        const message = formatIncomingMessage(parsedData);

        if (message.event === "on_chain_start") {
          addNewMessage(message);
        }

        if (message.event === "on_chat_model_stream") {
          buildOnLastMessage(message);
        }

        if (message.event === "on_chain_end") {
          finishLastMessage(message);
        }
        
      } catch (error) {
        console.error("Error parsing WebSocket message:", error);
      }
    };
    

    socket.onclose = () => {
      // console.log("WebSocket disconnected");
      setIsConnected(false);

      if (reconnectSocketRef.current) {
        setTimeout(() => {
          // console.log("Reconnecting...");
          connect();
        }, 2000);
      }
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
      socket.close(); // optional
    };
  };

  // use effect to connect socket and set up reconnect logic
  useEffect(() => {
    reconnectSocketRef.current = true;
    connect();

    return () => {
      reconnectSocketRef.current = false;
      if (socketRef.current) {
        socketRef.current.close();
      }
    };

  }, [url]);

  useEffect(() => {
    if (isConnected && !isChatOpen) {
      fetchStartChat();
      setIsChatOpen(true);
    }
  }, [isConnected, isChatOpen]);


  // Seperated reconnect function for manual reconnection
  const reconnect = () => {
    if (socketRef.current) {
      socketRef.current.close();
    }
    connect();
  };


  const sendMessage = (table_name: string, input: string) => {
    const formattedUserMessage = formatOutgoingMessage("User", table_name, input, "request");
    
    addNewMessage(formattedUserMessage);

    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(formattedUserMessage));
    } else {
      console.error("WebSocket is not open. Cannot send message.");
    }
  };

  const addNewMessage = (message: MessageInstance) => {
    setMessages((prevMessages) => [...prevMessages, message]);
  }

  const buildOnLastMessage = (deltaMessage: MessageInstance) => {
    setMessages((prevMessages) => {
      if (prevMessages.length === 0) {
        console.warn("No messages to update.");
        return prevMessages;
      }
      const updatedMessages = [...prevMessages];
      const lastMessage = updatedMessages[updatedMessages.length - 1];
      updatedMessages[updatedMessages.length - 1] = {
        ...lastMessage,
        message: deltaMessage.message,
      };
  
      return updatedMessages;
    });
  };

  const finishLastMessage = (message: MessageInstance) => {
    console.log("Finish last message: ", message);
    setMessages((prevMessages) => {
      if (prevMessages.length === 0) {
        console.warn("No messages to update.");
        return prevMessages;
      }
      const updatedMessages = [...prevMessages];
      const lastMessage = updatedMessages[updatedMessages.length - 1];

      updatedMessages[updatedMessages.length - 1] = {
        ...lastMessage,
        message: lastMessage.message,
        modified_query: message.modified_query,
        modified_query_label: message.modified_query_label
      };
  
      return updatedMessages;
    });
  };

  

  return (
    <ChatWebsocketContext.Provider value={{ isConnected, sendMessage, input: messages, messages, setMessages, reconnect, setIsChatOpen, isChatOpen }}>
      {children}
    </ChatWebsocketContext.Provider>
  );
};

export const useChatWebSocket = () => {
  const context = useContext(ChatWebsocketContext);
  if (!context) {
    throw new Error("useChatWebSocket must be used within a ChatWebsocketProvider");
  }
  return context;
};
