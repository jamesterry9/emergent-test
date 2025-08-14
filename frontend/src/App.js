import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Textarea } from './components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Badge } from './components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Switch } from './components/ui/switch';
import { Label } from './components/ui/label';
import { ScrollArea } from './components/ui/scroll-area';
import { Separator } from './components/ui/separator';
import { Avatar, AvatarFallback } from './components/ui/avatar';
import { MessageCircle, Plus, Bot, User, Settings, LogOut, Send } from 'lucide-react';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

function App() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [chatbots, setChatbots] = useState([]);
  const [selectedChatbot, setSelectedChatbot] = useState(null);
  const [conversation, setConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('home');

  // Auth states
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authMode, setAuthMode] = useState('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  // Create chatbot states
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newChatbot, setNewChatbot] = useState({
    name: '',
    description: '',
    introduction: '',
    is_censored: true
  });

  useEffect(() => {
    const savedToken = localStorage.getItem('token');
    if (savedToken) {
      setToken(savedToken);
      fetchUser();
    }
    fetchChatbots();
  }, []);

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete axios.defaults.headers.common['Authorization'];
    }
  }, [token]);

  const fetchUser = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/auth/me`);
      setUser(response.data);
    } catch (error) {
      console.error('Failed to fetch user:', error);
      if (error.response?.status === 401) {
        logout();
      }
    }
  };

  const fetchChatbots = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/chatbots`);
      setChatbots(response.data);
    } catch (error) {
      console.error('Failed to fetch chatbots:', error);
    }
  };

  const handleAuth = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const endpoint = authMode === 'login' ? 'login' : 'register';
      const response = await axios.post(`${API_BASE_URL}/api/auth/${endpoint}`, {
        username,
        password
      });
      
      const { access_token, user: userData } = response.data;
      setToken(access_token);
      setUser(userData);
      localStorage.setItem('token', access_token);
      setShowAuthModal(false);
      setUsername('');
      setPassword('');
    } catch (error) {
      alert(error.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
    setSelectedChatbot(null);
    setConversation(null);
    setMessages([]);
    setActiveTab('home');
  };

  const handleCreateChatbot = async (e) => {
    e.preventDefault();
    if (!user) return;

    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/api/chatbots`, newChatbot);
      setChatbots([response.data, ...chatbots]);
      setShowCreateModal(false);
      setNewChatbot({
        name: '',
        description: '',
        introduction: '',
        is_censored: true
      });
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to create chatbot');
    } finally {
      setLoading(false);
    }
  };

  const startConversation = async (chatbot) => {
    if (!user) {
      setShowAuthModal(true);
      return;
    }

    setSelectedChatbot(chatbot);
    setMessages([]);
    
    try {
      const response = await axios.post(`${API_BASE_URL}/api/chat/${chatbot.id}/start`);
      setConversation(response.data);
      setActiveTab('chat');
    } catch (error) {
      alert('Failed to start conversation');
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !conversation) return;

    const messageText = newMessage;
    setNewMessage('');
    setLoading(true);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/chat/${conversation.id}/message`, {
        message: messageText
      });
      
      setMessages([...messages, response.data.user_message, response.data.bot_response]);
    } catch (error) {
      alert('Failed to send message');
    } finally {
      setLoading(false);
    }
  };

  const AuthModal = () => (
    <Dialog open={showAuthModal} onOpenChange={setShowAuthModal}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{authMode === 'login' ? 'Login' : 'Sign Up'}</DialogTitle>
          <DialogDescription>
            {authMode === 'login' 
              ? 'Enter your credentials to access your account'
              : 'Create a new account to start creating chatbots'
            }
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleAuth} className="space-y-4">
          <div>
            <Label htmlFor="username">Username</Label>
            <Input
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
          <div>
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? 'Processing...' : (authMode === 'login' ? 'Login' : 'Sign Up')}
          </Button>
          <Button
            type="button"
            variant="ghost"
            className="w-full"
            onClick={() => setAuthMode(authMode === 'login' ? 'register' : 'login')}
          >
            {authMode === 'login' 
              ? "Don't have an account? Sign up"
              : "Already have an account? Login"
            }
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );

  const CreateChatbotModal = () => (
    <Dialog open={showCreateModal} onOpenChange={setShowCreateModal}>
      <DialogContent className="sm:max-w-[525px]">
        <DialogHeader>
          <DialogTitle>Create New Chatbot</DialogTitle>
          <DialogDescription>
            Design your AI chatbot with a unique personality and purpose
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleCreateChatbot} className="space-y-4">
          <div>
            <Label htmlFor="name">Chatbot Name</Label>
            <Input
              id="name"
              value={newChatbot.name}
              onChange={(e) => setNewChatbot({...newChatbot, name: e.target.value})}
              required
              placeholder="e.g., Alex the Helper"
            />
          </div>
          <div>
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={newChatbot.description}
              onChange={(e) => setNewChatbot({...newChatbot, description: e.target.value})}
              required
              placeholder="What does this chatbot do? What's its purpose?"
              rows={3}
            />
          </div>
          <div>
            <Label htmlFor="introduction">Introduction Message</Label>
            <Textarea
              id="introduction"
              value={newChatbot.introduction}
              onChange={(e) => setNewChatbot({...newChatbot, introduction: e.target.value})}
              required
              placeholder="How should the chatbot introduce itself when users start chatting?"
              rows={3}
            />
          </div>
          <div className="flex items-center space-x-2">
            <Switch
              id="censored"
              checked={!newChatbot.is_censored}
              onCheckedChange={(checked) => setNewChatbot({...newChatbot, is_censored: !checked})}
            />
            <Label htmlFor="censored">
              Uncensored (Allow roleplay and adult content)
            </Label>
          </div>
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? 'Creating...' : 'Create Chatbot'}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );

  const Header = () => (
    <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between px-4">
        <div className="flex items-center space-x-2">
          <Bot className="h-6 w-6 text-primary" />
          <h1 className="text-xl font-bold">ChatBot Creator</h1>
        </div>
        
        <div className="flex items-center space-x-4">
          {user ? (
            <>
              <Button
                onClick={() => setShowCreateModal(true)}
                className="hidden sm:flex items-center space-x-2"
              >
                <Plus className="h-4 w-4" />
                <span>Create Bot</span>
              </Button>
              <div className="flex items-center space-x-2">
                <Avatar>
                  <AvatarFallback>
                    {user.username.charAt(0).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <span className="hidden sm:inline">{user.username}</span>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={logout}
                >
                  <LogOut className="h-4 w-4" />
                </Button>
              </div>
            </>
          ) : (
            <Button onClick={() => setShowAuthModal(true)}>
              Login
            </Button>
          )}
        </div>
      </div>
    </header>
  );

  const ChatbotCard = ({ chatbot }) => (
    <Card className="cursor-pointer hover:shadow-lg transition-shadow duration-200" onClick={() => startConversation(chatbot)}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-2">
            <Avatar>
              <AvatarFallback>
                {chatbot.name.charAt(0).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <div>
              <CardTitle className="text-lg">{chatbot.name}</CardTitle>
              <CardDescription className="text-sm">
                by {chatbot.creator_username}
              </CardDescription>
            </div>
          </div>
          <div className="flex flex-col space-y-1">
            <Badge variant={chatbot.is_censored ? "secondary" : "destructive"}>
              {chatbot.is_censored ? "Safe" : "Uncensored"}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground line-clamp-3">
          {chatbot.description}
        </p>
        <div className="mt-3 flex items-center justify-between">
          <Button size="sm" className="flex items-center space-x-1">
            <MessageCircle className="h-3 w-3" />
            <span>Chat Now</span>
          </Button>
          <span className="text-xs text-muted-foreground">
            {new Date(chatbot.created_at).toLocaleDateString()}
          </span>
        </div>
      </CardContent>
    </Card>
  );

  const ChatInterface = () => (
    <div className="flex flex-col h-full">
      {selectedChatbot && (
        <div className="border-b p-4 bg-muted/50">
          <div className="flex items-center space-x-3">
            <Avatar>
              <AvatarFallback>
                {selectedChatbot.name.charAt(0).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <div>
              <h3 className="font-semibold">{selectedChatbot.name}</h3>
              <p className="text-sm text-muted-foreground">
                {selectedChatbot.description}
              </p>
            </div>
            <Badge variant={selectedChatbot.is_censored ? "secondary" : "destructive"}>
              {selectedChatbot.is_censored ? "Safe" : "Uncensored"}
            </Badge>
          </div>
        </div>
      )}
      
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4">
          {messages.length === 0 && selectedChatbot && (
            <div className="text-center p-8 text-muted-foreground">
              <Bot className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>Start a conversation with {selectedChatbot.name}!</p>
              <p className="text-sm mt-2">{selectedChatbot.introduction}</p>
            </div>
          )}
          
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.sender_type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[70%] rounded-lg px-4 py-2 ${
                  message.sender_type === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted'
                }`}
              >
                <div className="flex items-center space-x-2 mb-1">
                  {message.sender_type === 'user' ? (
                    <User className="h-3 w-3" />
                  ) : (
                    <Bot className="h-3 w-3" />
                  )}
                  <span className="font-medium text-xs">
                    {message.sender_type === 'user' ? 'You' : selectedChatbot?.name}
                  </span>
                  <span className="text-xs opacity-70">
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <p className="whitespace-pre-wrap">{message.content}</p>
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>
      
      <div className="border-t p-4">
        <form onSubmit={sendMessage} className="flex space-x-2">
          <Input
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            placeholder="Type your message..."
            disabled={loading || !conversation}
            className="flex-1"
          />
          <Button type="submit" disabled={loading || !newMessage.trim()}>
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col h-screen bg-background">
      <Header />
      
      <main className="flex-1 overflow-hidden">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full">
          <div className="border-b px-4">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="home">Browse Chatbots</TabsTrigger>
              <TabsTrigger value="chat" disabled={!selectedChatbot}>
                Chat {selectedChatbot ? `with ${selectedChatbot.name}` : ''}
              </TabsTrigger>
            </TabsList>
          </div>
          
          <TabsContent value="home" className="p-4 h-full overflow-auto">
            <div className="max-w-6xl mx-auto">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-2xl font-bold">Discover AI Chatbots</h2>
                  <p className="text-muted-foreground">
                    Chat with unique AI personalities created by the community
                  </p>
                </div>
                {user && (
                  <Button
                    onClick={() => setShowCreateModal(true)}
                    className="flex items-center space-x-2"
                  >
                    <Plus className="h-4 w-4" />
                    <span>Create Bot</span>
                  </Button>
                )}
              </div>
              
              {chatbots.length === 0 ? (
                <div className="text-center py-12">
                  <Bot className="h-16 w-16 mx-auto mb-4 text-muted-foreground/50" />
                  <h3 className="text-lg font-semibold mb-2">No chatbots yet</h3>
                  <p className="text-muted-foreground mb-4">
                    Be the first to create an AI chatbot!
                  </p>
                  {user && (
                    <Button onClick={() => setShowCreateModal(true)}>
                      Create Your First Bot
                    </Button>
                  )}
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {chatbots.map((chatbot) => (
                    <ChatbotCard key={chatbot.id} chatbot={chatbot} />
                  ))}
                </div>
              )}
            </div>
          </TabsContent>
          
          <TabsContent value="chat" className="h-full">
            {selectedChatbot ? (
              <ChatInterface />
            ) : (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <MessageCircle className="h-16 w-16 mx-auto mb-4 text-muted-foreground/50" />
                  <h3 className="text-lg font-semibold mb-2">No conversation selected</h3>
                  <p className="text-muted-foreground">
                    Go back to browse and select a chatbot to start chatting
                  </p>
                </div>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>
      
      <AuthModal />
      <CreateChatbotModal />
    </div>
  );
}

export default App;