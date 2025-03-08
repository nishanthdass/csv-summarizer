import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import { useFetchDataDatabase } from "../hooks/fetch_hooks/useFetchDataDatabase";
import { set } from "lodash";

interface TokenObject {
  run_id: string | null;
  model_name: string;
  tool_call_name: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
}
interface MessageInstance {
  role: string;
  table_name: string;
  pdf_name: string;
  event: string;
  message: string;
  time?: string;
  thread_id?: string;
  token_object?: TokenObject[]; 
  answer_query?: string | null;
  visualizing_query?: string | null;
  viewing_query_label?: string | null;
}

interface ChatWebsocketContextValue {
  isConnected: boolean;
  sendMessage: (table_name: string, pdf_name: string, input: string) => void;
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

  useEffect(() => {
    console.log("Messages changed:", messages);
  }, [messages]);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectSocketRef = useRef(true);

  const { fetchStartChat } = useFetchDataDatabase();


  const formatIncomingMessage = (data: any): MessageInstance => {
    const run_id = data.run_id || null;
    const input_tokens = data.input_tokens || 0;
    const output_tokens = data.output_tokens || 0;
    const total_tokens = data.total_tokens || 0;
    let token_object: TokenObject[] = [];

  if (run_id || input_tokens || output_tokens || total_tokens) {
    token_object = [
      {
        run_id: run_id,
        model_name: data.model_name,
        tool_call_name: data.tool_call_name,
        input_tokens: input_tokens,
        output_tokens: output_tokens,
        total_tokens: total_tokens,
      },
    ];
  }
  
    const message: MessageInstance = {
      role: String(data.role),
      table_name: String(data.table_name),
      pdf_name: String(data.pdf_name),
      event: String(data.event),
      message: String(data.message),
      time: data.time ? String(data.time) : "0",
      thread_id: data.thread_id ? String(data.thread_id) : "",
      token_object: token_object,
      answer_query: convertStringNullToNull(data.answer_query),
      visualizing_query: convertStringNullToNull(data.visualizing_query),
      viewing_query_label: convertStringNullToNull(data.viewing_query_label),
    };
  
    return message;
  };
  
  
  const convertStringNullToNull = (value: any): any => {
    return value === "null" ? null : value;
  };
  

  const formatOutgoingMessage = (role: string, table_name: string, pdf_name: string, message: string, event: string): MessageInstance => ({
    role,
    table_name,
    pdf_name,
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
          // console.log("on_chat_model_stream");
          // console.log(messages);
          // console.log(message);
          buildOnLastMessage(message);
        }

        if (message.event === "on_chat_model_end") {
          setTokenCountPerMessage(message);
        }

        if (message.event === "on_query_stream") {
          console.log("on_query_stream");
          // console.log(messages);
          // console.log(message);
          addToLastMessage(message);
        }

        if (message.event === "on_chain_end") {
          // console.log("on_chain_end");
          // console.log(messages);
          // console.log(message);
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


  const sendMessage = (table_name: string, pdf_name: string, input: string) => {
    const formattedUserMessage = formatOutgoingMessage("User", table_name, pdf_name, input, "request");
    
    addNewMessage(formattedUserMessage);

    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(formattedUserMessage));
    } else {
      console.error("WebSocket is not open. Cannot send message.");
    }
  };

  const addNewMessage = (message: MessageInstance) => {
    const newMessage = {
      ...message,
      time: message.time || "0",
    };
  
    setMessages((prevMessages) => [...prevMessages, newMessage]);
  };
  

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
        time: deltaMessage.time
      };
  
      return updatedMessages;
    });
  };

  const addToLastMessage = (deltaMessage: MessageInstance) => {
    setMessages((prevMessages) => {
      if (prevMessages.length === 0) {
        console.warn("No messages to update.");
        return prevMessages;
      }
      const updatedMessages = [...prevMessages];
      const lastMessage = updatedMessages[updatedMessages.length - 1];
      updatedMessages[updatedMessages.length - 1] = {
        ...lastMessage,
        message: lastMessage.message + deltaMessage.message,
        time: deltaMessage.time,
        visualizing_query: deltaMessage.visualizing_query,
        viewing_query_label: deltaMessage.viewing_query_label
      };
  
      return updatedMessages;
    });
  }

  const finishLastMessage = (message: MessageInstance) => {
    setMessages((prevMessages) => {
      if (prevMessages.length === 0) {
        console.warn("No messages to update.");
        return prevMessages;
      }
      const updatedMessages = [...prevMessages];
      const lastMessage = updatedMessages[updatedMessages.length - 1];

      updatedMessages[updatedMessages.length - 1] = {
        ...lastMessage,
        message: message.message,
        time: message.time,
        visualizing_query: message.visualizing_query,
        viewing_query_label: message.viewing_query_label
      };
  
      return updatedMessages;
    });
  };

  const setTokenCountPerMessage = (incomingMessage: MessageInstance) => {
    setMessages((prevMessages) => {
      if (prevMessages.length === 0) {
        return prevMessages;
      }
  
      const updatedMessages = [...prevMessages];
      const lastIndex = updatedMessages.length - 1;
      const lastMessage = updatedMessages[lastIndex];

      const existingTokens = lastMessage.token_object || [];
      const newTokens = incomingMessage.token_object || [];
  
      const mergedTokenObject = [...existingTokens, ...newTokens];
  
      updatedMessages[lastIndex] = {
        ...lastMessage,
        token_object: mergedTokenObject,
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
