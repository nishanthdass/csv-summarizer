import { add } from "lodash";
import React, { createContext, useContext, useEffect, useRef, useState } from "react";

interface Message {
  role: string;
  table_name: string;
  event: string;
  message: string;
}

interface ChatWebsocketContextValue {
  isInProgress: boolean;
  setIsInProgress: React.Dispatch<React.SetStateAction<boolean>>;
  isConnected: boolean;
  sendMessage: (table_name: string, input: string) => void;
  input: Message[];
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  reconnect: () => void;
}

interface ChatWebsocketProviderProps {
  url: string;
  children: React.ReactNode;
}

const ChatWebsocketContext = createContext<ChatWebsocketContextValue | undefined>(undefined);

export const ChatWebsocketProvider: React.FC<ChatWebsocketProviderProps> = ({ url, children }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [ connectionKey, setConnectionKey] = useState(0);
  const [messages, setMessages] = useState<Message[]>([]);
  const socketRef = useRef<WebSocket | null>(null);
  const [isInProgress, setIsInProgress] = useState(false);

  const formatIncomingMessage = (data: any): Message => {
    // console.log("convertToMessage data: ", data, typeof data);
    return {
      role: String(data.role),
      table_name: String(data.table_name),
      event: String(data.event),
      message: String(data.message),
    };
  };

  const formatOutgoingMessage = (role: string, table_name: string, message: string, event: string): Message => ({
    role,
    table_name,
    event,
    message,
  });


  
  useEffect(() => {
    const socket = new WebSocket(url);
    socketRef.current = socket;

    socket.onopen = () => {
      console.log("WebSocket connected");
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
        
      } catch (error) {
        console.error("Error parsing WebSocket message:", error);
      }
    };
    

    socket.onclose = () => {
      console.log("WebSocket disconnected");
      setIsConnected(false);
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    return () => {
      console.log("Cleaning up WebSocket");
      socket.close();
    };
  }, [url, connectionKey]);

  const reconnect = () => {
    console.log("Reconnecting WebSocket...");
    setConnectionKey((prevKey) => prevKey + 1); // Update connectionKey to re-trigger useEffect
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

  const addNewMessage = (message: Message) => {
    setMessages((prevMessages) => [...prevMessages, message]);
  }

  const buildOnLastMessage = (deltaMessage: Message) => {
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

  

  return (
    <ChatWebsocketContext.Provider value={{ isInProgress, setIsInProgress, isConnected, sendMessage, input: messages, messages, setMessages, reconnect }}>
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
