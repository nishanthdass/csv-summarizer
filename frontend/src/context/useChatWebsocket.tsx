import { add, set } from "lodash";
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
}

interface ChatWebsocketProviderProps {
  url: string;
  children: React.ReactNode;
}

const ChatWebsocketContext = createContext<ChatWebsocketContextValue | undefined>(undefined);

export const ChatWebsocketProvider: React.FC<ChatWebsocketProviderProps> = ({ url, children }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentMessage, setCurrentMessage] = useState<Message | null>(null);
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
    console.log("Messages updated:", messages);
  }, [messages]);
  
  useEffect(() => {
    console.log("Initializing WebSocket...");
    const socket = new WebSocket(url);
    socketRef.current = socket;

    socket.onopen = () => {
      console.log("WebSocket connected");
      setIsConnected(true);
    };

    socket.onmessage = (event) => {
      try {
        const parsedData = JSON.parse(event.data);
        // console.log("WebSocket message received:", parsedData, typeof parsedData, typeof event.data);
        const message = formatIncomingMessage(parsedData);
        if (message.event === "created") {
          buildOnLastMessage(message);
        }

        if (message.event === "delta") {
          buildOnLastMessage(message);
        }
        
        if (message.event === "complete") {
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
  }, [url]);

  const sendMessage = (table_name: string, input: string) => {
    const formattedUserMessage = formatOutgoingMessage("User", table_name, input, "request");
    
    addNewMessage(formattedUserMessage);

    const formattedChatbotMessage = formatOutgoingMessage("assistant", table_name, "", "request");

    addNewMessage(formattedChatbotMessage);

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
        return prevMessages; // Return the array unchanged if empty
      }
  
      // Clone the messages array
      const updatedMessages = [...prevMessages];
  
      // Get the last message and update its `message` part
      const lastMessage = updatedMessages[updatedMessages.length - 1];
      updatedMessages[updatedMessages.length - 1] = {
        ...lastMessage,
        message: lastMessage.message + deltaMessage.message,
      };
  
      return updatedMessages;
    });
  };
  




  return (
    <ChatWebsocketContext.Provider value={{ isInProgress, setIsInProgress, isConnected, sendMessage, input: messages, messages, setMessages }}>
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
