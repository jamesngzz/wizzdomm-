import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import CreateExam from "./pages/CreateExam";
import ExamList from "./pages/ExamList";
import CropExam from "./pages/CropExam";
import Submissions from "./pages/Submissions";
import CropSubmission from "./pages/CropSubmission";
import Grading from "./pages/Grading";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/exams" replace />} />
          <Route path="/exams" element={<Layout><ExamList /></Layout>} />
          <Route path="/exams/create" element={<Layout><CreateExam /></Layout>} />
          <Route path="/exams/crop" element={<Layout><CropExam /></Layout>} />
          <Route path="/submissions" element={<Layout><Submissions /></Layout>} />
          <Route path="/submissions/crop" element={<Layout><CropSubmission /></Layout>} />
          <Route path="/grading" element={<Layout><Grading /></Layout>} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
