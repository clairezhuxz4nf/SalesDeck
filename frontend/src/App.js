import { useState, useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from "react-router-dom";
import axios from "axios";
import { Toaster } from "@/components/ui/sonner";
import { toast } from "sonner";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Loader2, Plus, Trash2, FileText, Briefcase, Users, TrendingUp, Presentation, LogOut, Sparkles } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const axiosInstance = axios.create({
  baseURL: API,
  withCredentials: true,
});

function LandingPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const sessionId = location.hash.replace('#session_id=', '');
    if (sessionId) {
      processSessionId(sessionId);
    } else {
      checkExistingSession();
    }
  }, [location]);

  const processSessionId = async (sessionId) => {
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('session_id', sessionId);
      
      await axiosInstance.post('/auth/session', formData);
      window.history.replaceState({}, document.title, window.location.pathname);
      navigate('/dashboard');
    } catch (error) {
      console.error('Session processing failed:', error);
      toast.error('Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const checkExistingSession = async () => {
    try {
      await axiosInstance.get('/auth/me');
      navigate('/dashboard');
    } catch (error) {
      // Not authenticated, stay on landing
    }
  };

  const handleLogin = () => {
    const redirectUrl = `${window.location.origin}/dashboard`;
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
        <div className="text-center" data-testid="loading-screen">
          <Loader2 className="h-12 w-12 animate-spin mx-auto text-indigo-600" />
          <p className="mt-4 text-slate-600">Authenticating...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto text-center">
          <div className="mb-8" data-testid="landing-header">
            <Presentation className="h-20 w-20 mx-auto text-indigo-600 mb-6" />
            <h1 className="text-5xl lg:text-6xl font-bold text-slate-900 mb-6">
              AI Sales Deck Generator
            </h1>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto mb-8">
              Generate customized, high-impact B2B SaaS sales presentations in minutes. 
              Save 10-15 hours per week and accelerate your sales cycle.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6 mb-12">
            <Card className="border-indigo-200 hover:shadow-lg transition-shadow">
              <CardContent className="pt-6">
                <Sparkles className="h-10 w-10 text-indigo-600 mx-auto mb-4" />
                <h3 className="font-semibold text-slate-900 mb-2">AI-Powered</h3>
                <p className="text-sm text-slate-600">Generate tailored presentations using advanced AI</p>
              </CardContent>
            </Card>
            <Card className="border-indigo-200 hover:shadow-lg transition-shadow">
              <CardContent className="pt-6">
                <TrendingUp className="h-10 w-10 text-indigo-600 mx-auto mb-4" />
                <h3 className="font-semibold text-slate-900 mb-2">Save Time</h3>
                <p className="text-sm text-slate-600">10-15 hours saved per week on deck creation</p>
              </CardContent>
            </Card>
            <Card className="border-indigo-200 hover:shadow-lg transition-shadow">
              <CardContent className="pt-6">
                <Briefcase className="h-10 w-10 text-indigo-600 mx-auto mb-4" />
                <h3 className="font-semibold text-slate-900 mb-2">Close Faster</h3>
                <p className="text-sm text-slate-600">Accelerate sales cycles with targeted pitches</p>
              </CardContent>
            </Card>
          </div>

          <Button 
            onClick={handleLogin} 
            size="lg" 
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-8 py-6 text-lg"
            data-testid="login-button"
          >
            Get Started with Google
          </Button>
        </div>
      </div>
    </div>
  );
}

function Dashboard() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [clients, setClients] = useState([]);
  const [assets, setAssets] = useState([]);
  const [leads, setLeads] = useState([]);
  const [decks, setDecks] = useState([]);
  const [activeTab, setActiveTab] = useState("assets");
  
  // Form states
  const [clientForm, setClientForm] = useState({ name: '', industry: '', description: '' });
  const [assetForm, setAssetForm] = useState({ type: 'product_description', name: '', content: '' });
  const [leadForm, setLeadForm] = useState({ client_id: '', project_scope: '', notes: '' });
  const [generating, setGenerating] = useState(false);
  const [selectedDeck, setSelectedDeck] = useState(null);

  useEffect(() => {
    fetchUser();
  }, []);

  useEffect(() => {
    if (user) {
      fetchData();
    }
  }, [user, activeTab]);

  const fetchUser = async () => {
    try {
      const response = await axiosInstance.get('/auth/me');
      setUser(response.data);
    } catch (error) {
      navigate('/');
    } finally {
      setLoading(false);
    }
  };

  const fetchData = async () => {
    try {
      const [clientsRes, assetsRes, leadsRes, decksRes] = await Promise.all([
        axiosInstance.get('/clients'),
        axiosInstance.get('/assets'),
        axiosInstance.get('/leads'),
        axiosInstance.get('/decks')
      ]);
      setClients(clientsRes.data);
      setAssets(assetsRes.data);
      setLeads(leadsRes.data);
      setDecks(decksRes.data);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    }
  };

  const handleLogout = async () => {
    try {
      await axiosInstance.post('/auth/logout');
      navigate('/');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  const createClient = async (e) => {
    e.preventDefault();
    try {
      await axiosInstance.post('/clients', clientForm);
      setClientForm({ name: '', industry: '', description: '' });
      toast.success('Client added successfully');
      fetchData();
    } catch (error) {
      toast.error('Failed to add client');
    }
  };

  const deleteClient = async (id) => {
    try {
      await axiosInstance.delete(`/clients/${id}`);
      toast.success('Client deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete client');
    }
  };

  const createAsset = async (e) => {
    e.preventDefault();
    try {
      await axiosInstance.post('/assets', assetForm);
      setAssetForm({ type: 'product_description', name: '', content: '' });
      toast.success('Asset added successfully');
      fetchData();
    } catch (error) {
      toast.error('Failed to add asset');
    }
  };

  const deleteAsset = async (id) => {
    try {
      await axiosInstance.delete(`/assets/${id}`);
      toast.success('Asset deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete asset');
    }
  };

  const createLead = async (e) => {
    e.preventDefault();
    try {
      await axiosInstance.post('/leads', leadForm);
      setLeadForm({ client_id: '', project_scope: '', notes: '' });
      toast.success('Lead created successfully');
      fetchData();
    } catch (error) {
      toast.error('Failed to create lead');
    }
  };

  const deleteLead = async (id) => {
    try {
      await axiosInstance.delete(`/leads/${id}`);
      toast.success('Lead deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete lead');
    }
  };

  const generateDeck = async (leadId) => {
    setGenerating(true);
    try {
      const response = await axiosInstance.post('/decks/generate', { lead_id: leadId });
      toast.success('Sales deck generated!');
      fetchData();
      setSelectedDeck(response.data);
    } catch (error) {
      toast.error('Failed to generate deck');
    } finally {
      setGenerating(false);
    }
  };

  const viewDeck = async (deckId) => {
    try {
      const response = await axiosInstance.get(`/decks/${deckId}`);
      setSelectedDeck(response.data);
    } catch (error) {
      toast.error('Failed to load deck');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      <header className="bg-white border-b border-slate-200 shadow-sm">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <Presentation className="h-8 w-8 text-indigo-600" />
            <h1 className="text-2xl font-bold text-slate-900">Sales Deck AI</h1>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-slate-600" data-testid="user-name">{user?.name}</span>
            <Button variant="outline" size="sm" onClick={handleLogout} data-testid="logout-button">
              <LogOut className="h-4 w-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="bg-white border border-slate-200 p-1" data-testid="tabs-list">
            <TabsTrigger value="assets" className="data-[state=active]:bg-indigo-100" data-testid="tab-assets">
              <FileText className="h-4 w-4 mr-2" />
              Assets
            </TabsTrigger>
            <TabsTrigger value="clients" className="data-[state=active]:bg-indigo-100" data-testid="tab-clients">
              <Users className="h-4 w-4 mr-2" />
              Clients
            </TabsTrigger>
            <TabsTrigger value="leads" className="data-[state=active]:bg-indigo-100" data-testid="tab-leads">
              <Briefcase className="h-4 w-4 mr-2" />
              Leads
            </TabsTrigger>
            <TabsTrigger value="decks" className="data-[state=active]:bg-indigo-100" data-testid="tab-decks">
              <Presentation className="h-4 w-4 mr-2" />
              Generated Decks
            </TabsTrigger>
          </TabsList>

          <TabsContent value="assets" className="space-y-6" data-testid="tab-content-assets">
            <Card>
              <CardHeader>
                <CardTitle>Add Knowledge Asset</CardTitle>
                <CardDescription>Product descriptions, use cases, and documentation</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={createAsset} className="space-y-4">
                  <div>
                    <Label>Type</Label>
                    <Select value={assetForm.type} onValueChange={(val) => setAssetForm({...assetForm, type: val})}>
                      <SelectTrigger data-testid="asset-type-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="product_description">Product Description</SelectItem>
                        <SelectItem value="use_case">Industry Use Case</SelectItem>
                        <SelectItem value="general">General Asset</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Name</Label>
                    <Input
                      value={assetForm.name}
                      onChange={(e) => setAssetForm({...assetForm, name: e.target.value})}
                      placeholder="Asset name"
                      required
                      data-testid="asset-name-input"
                    />
                  </div>
                  <div>
                    <Label>Content</Label>
                    <Textarea
                      value={assetForm.content}
                      onChange={(e) => setAssetForm({...assetForm, content: e.target.value})}
                      placeholder="Paste your content here..."
                      rows={6}
                      required
                      data-testid="asset-content-textarea"
                    />
                  </div>
                  <Button type="submit" className="bg-indigo-600 hover:bg-indigo-700" data-testid="add-asset-button">
                    <Plus className="h-4 w-4 mr-2" />
                    Add Asset
                  </Button>
                </form>
              </CardContent>
            </Card>

            <div className="grid gap-4">
              {assets.map((asset) => (
                <Card key={asset.id} data-testid={`asset-card-${asset.id}`}>
                  <CardHeader>
                    <div className="flex justify-between items-start">
                      <div>
                        <CardTitle className="text-lg">{asset.name}</CardTitle>
                        <CardDescription className="capitalize">{asset.type.replace('_', ' ')}</CardDescription>
                      </div>
                      <Button variant="ghost" size="sm" onClick={() => deleteAsset(asset.id)} data-testid={`delete-asset-${asset.id}`}>
                        <Trash2 className="h-4 w-4 text-red-500" />
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-slate-600 whitespace-pre-wrap">{asset.content}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="clients" className="space-y-6" data-testid="tab-content-clients">
            <Card>
              <CardHeader>
                <CardTitle>Add Client</CardTitle>
                <CardDescription>Manage your client information</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={createClient} className="space-y-4">
                  <div>
                    <Label>Client Name</Label>
                    <Input
                      value={clientForm.name}
                      onChange={(e) => setClientForm({...clientForm, name: e.target.value})}
                      placeholder="Company name"
                      required
                      data-testid="client-name-input"
                    />
                  </div>
                  <div>
                    <Label>Industry</Label>
                    <Input
                      value={clientForm.industry}
                      onChange={(e) => setClientForm({...clientForm, industry: e.target.value})}
                      placeholder="e.g., Healthcare, Finance, Technology"
                      required
                      data-testid="client-industry-input"
                    />
                  </div>
                  <div>
                    <Label>Description</Label>
                    <Textarea
                      value={clientForm.description}
                      onChange={(e) => setClientForm({...clientForm, description: e.target.value})}
                      placeholder="Brief company description..."
                      rows={4}
                      required
                      data-testid="client-description-textarea"
                    />
                  </div>
                  <Button type="submit" className="bg-indigo-600 hover:bg-indigo-700" data-testid="add-client-button">
                    <Plus className="h-4 w-4 mr-2" />
                    Add Client
                  </Button>
                </form>
              </CardContent>
            </Card>

            <div className="grid md:grid-cols-2 gap-4">
              {clients.map((client) => (
                <Card key={client.id} data-testid={`client-card-${client.id}`}>
                  <CardHeader>
                    <div className="flex justify-between items-start">
                      <div>
                        <CardTitle className="text-lg">{client.name}</CardTitle>
                        <CardDescription>{client.industry}</CardDescription>
                      </div>
                      <Button variant="ghost" size="sm" onClick={() => deleteClient(client.id)} data-testid={`delete-client-${client.id}`}>
                        <Trash2 className="h-4 w-4 text-red-500" />
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-slate-600">{client.description}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="leads" className="space-y-6" data-testid="tab-content-leads">
            <Card>
              <CardHeader>
                <CardTitle>Create Lead</CardTitle>
                <CardDescription>Link a client and define project scope</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={createLead} className="space-y-4">
                  <div>
                    <Label>Select Client</Label>
                    <Select value={leadForm.client_id} onValueChange={(val) => setLeadForm({...leadForm, client_id: val})}>
                      <SelectTrigger data-testid="lead-client-select">
                        <SelectValue placeholder="Choose a client" />
                      </SelectTrigger>
                      <SelectContent>
                        {clients.map((client) => (
                          <SelectItem key={client.id} value={client.id}>{client.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Project Scope</Label>
                    <Textarea
                      value={leadForm.project_scope}
                      onChange={(e) => setLeadForm({...leadForm, project_scope: e.target.value})}
                      placeholder="Describe the project requirements..."
                      rows={4}
                      required
                      data-testid="lead-scope-textarea"
                    />
                  </div>
                  <div>
                    <Label>Notes</Label>
                    <Textarea
                      value={leadForm.notes}
                      onChange={(e) => setLeadForm({...leadForm, notes: e.target.value})}
                      placeholder="Additional notes, pain points, meeting minutes..."
                      rows={4}
                      required
                      data-testid="lead-notes-textarea"
                    />
                  </div>
                  <Button type="submit" className="bg-indigo-600 hover:bg-indigo-700" data-testid="add-lead-button">
                    <Plus className="h-4 w-4 mr-2" />
                    Create Lead
                  </Button>
                </form>
              </CardContent>
            </Card>

            <div className="grid gap-4">
              {leads.map((lead) => (
                <Card key={lead.id} data-testid={`lead-card-${lead.id}`}>
                  <CardHeader>
                    <div className="flex justify-between items-start">
                      <div>
                        <CardTitle className="text-lg">{lead.client_name}</CardTitle>
                        <CardDescription className="capitalize">{lead.status}</CardDescription>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          onClick={() => generateDeck(lead.id)}
                          disabled={generating}
                          className="bg-indigo-600 hover:bg-indigo-700"
                          data-testid={`generate-deck-${lead.id}`}
                        >
                          {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4 mr-2" />}
                          Generate Deck
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => deleteLead(lead.id)} data-testid={`delete-lead-${lead.id}`}>
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <p className="text-sm font-medium text-slate-700">Project Scope:</p>
                      <p className="text-sm text-slate-600 whitespace-pre-wrap">{lead.project_scope}</p>
                      <p className="text-sm font-medium text-slate-700 mt-4">Notes:</p>
                      <p className="text-sm text-slate-600 whitespace-pre-wrap">{lead.notes}</p>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="decks" className="space-y-6" data-testid="tab-content-decks">
            <div className="grid md:grid-cols-2 gap-4">
              {decks.map((deck) => (
                <Card key={deck.id} className="hover:shadow-lg transition-shadow cursor-pointer" onClick={() => viewDeck(deck.id)} data-testid={`deck-card-${deck.id}`}>
                  <CardHeader>
                    <CardTitle className="text-lg">{deck.content.title || deck.lead_name}</CardTitle>
                    <CardDescription>
                      {new Date(deck.created_at).toLocaleDateString()} • {deck.content.slides?.length || 0} slides
                    </CardDescription>
                  </CardHeader>
                </Card>
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </main>

      <Dialog open={selectedDeck !== null} onOpenChange={() => setSelectedDeck(null)}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto" data-testid="deck-viewer-dialog">
          {selectedDeck && (
            <div className="presentation-viewer">
              <DialogHeader>
                <DialogTitle className="text-2xl">{selectedDeck.content.title}</DialogTitle>
              </DialogHeader>
              <div className="space-y-8 mt-6">
                {selectedDeck.content.slides?.map((slide, index) => (
                  <div key={index} className="slide-content p-6 bg-gradient-to-br from-indigo-50 to-blue-50 rounded-lg border border-indigo-200" data-testid={`slide-${index}`}>
                    {slide.type === 'title' && (
                      <div className="text-center py-12">
                        <h2 className="text-4xl font-bold text-slate-900 mb-4">{slide.title}</h2>
                        <p className="text-xl text-slate-600">{slide.subtitle}</p>
                      </div>
                    )}
                    {slide.type === 'problem' && (
                      <div>
                        <h3 className="text-2xl font-bold text-slate-900 mb-4">{slide.title}</h3>
                        <ul className="space-y-2">
                          {slide.points?.map((point, i) => (
                            <li key={i} className="flex items-start gap-2">
                              <span className="text-indigo-600 font-bold">•</span>
                              <span className="text-slate-700">{point}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {slide.type === 'solution' && (
                      <div>
                        <h3 className="text-2xl font-bold text-slate-900 mb-4">{slide.title}</h3>
                        <p className="text-slate-700 mb-4">{slide.description}</p>
                        <ul className="space-y-2">
                          {slide.points?.map((point, i) => (
                            <li key={i} className="flex items-start gap-2">
                              <span className="text-indigo-600 font-bold">✓</span>
                              <span className="text-slate-700">{point}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {slide.type === 'features' && (
                      <div>
                        <h3 className="text-2xl font-bold text-slate-900 mb-4">{slide.title}</h3>
                        <div className="grid md:grid-cols-2 gap-4">
                          {slide.features?.map((feature, i) => (
                            <div key={i} className="bg-white p-4 rounded-lg">
                              <h4 className="font-semibold text-slate-900 mb-2">{feature.name}</h4>
                              <p className="text-sm text-slate-600">{feature.description}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {slide.type === 'use_case' && (
                      <div>
                        <h3 className="text-2xl font-bold text-slate-900 mb-4">{slide.title}</h3>
                        <p className="text-slate-700">{slide.description}</p>
                      </div>
                    )}
                    {slide.type === 'roi' && (
                      <div>
                        <h3 className="text-2xl font-bold text-slate-900 mb-4">{slide.title}</h3>
                        <div className="grid md:grid-cols-2 gap-4">
                          {slide.metrics?.map((metric, i) => (
                            <div key={i} className="bg-white p-6 rounded-lg text-center">
                              <p className="text-3xl font-bold text-indigo-600 mb-2">{metric.value}</p>
                              <p className="text-sm text-slate-600">{metric.label}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {slide.type === 'cta' && (
                      <div className="text-center py-8">
                        <h3 className="text-2xl font-bold text-slate-900 mb-4">{slide.title}</h3>
                        <p className="text-slate-700 mb-6">{slide.description}</p>
                        <div className="inline-block px-6 py-3 bg-indigo-600 text-white rounded-lg font-semibold">
                          {slide.action}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <Toaster position="top-right" />
    </div>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;