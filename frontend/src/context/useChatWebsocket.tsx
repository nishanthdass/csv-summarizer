import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import { useFetchDataDatabase } from "../hooks/fetch_hooks/useFetchDataDatabase";


interface Message {
  role: string;
  table_name: string;
  event: string;
  message: string;
  is_action?: boolean
}

interface ChatWebsocketContextValue {
  isConnected: boolean;
  sendMessage: (table_name: string, input: string) => void;
  input: Message[];
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
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
  const [ messages, setMessages ] = useState<Message[]>([]);


  const socketRef = useRef<WebSocket | null>(null);
  const reconnectSocketRef = useRef(true);

  const { fetchStartChat } = useFetchDataDatabase();


  const formatIncomingMessage = (data: any): Message => {

    return {
      role: String(data.role),
      table_name: String(data.table_name),
      event: String(data.event),
      message: String(data.message),
      is_action: Boolean(data.is_action),
    };
  };

  const formatOutgoingMessage = (role: string, table_name: string, message: string, event: string): Message => ({
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
        is_action: deltaMessage.is_action
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
