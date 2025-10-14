import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FileText, Users, CheckCircle, Clock, TrendingUp, Upload, Crop, Brain, FileOutput } from "lucide-react";
import { Link } from "react-router-dom";

const Dashboard = () => {
  const stats = [
    {
      icon: FileText,
      label: "Tổng số đề thi",
      value: "3",
      change: "+12% tháng này",
      color: "bg-primary",
    },
    {
      icon: Users,
      label: "Bài nộp",
      value: "0",
      change: "+8% tuần này",
      color: "bg-success",
    },
    {
      icon: CheckCircle,
      label: "Đã chấm",
      value: "0",
      change: "",
      color: "bg-info",
    },
    {
      icon: Clock,
      label: "Chờ chấm",
      value: "0",
      change: "",
      color: "bg-warning",
    },
  ];

  const guides = [
    {
      step: "1",
      title: "Tạo đề thi",
      description: "Upload ảnh đề bài và câu hỏi",
      icon: Upload,
    },
    {
      step: "2",
      title: "Nhận bài làm",
      description: "Upload ảnh bài làm của học sinh",
      icon: Users,
    },
    {
      step: "3",
      title: "AI chấm bài",
      description: "Hệ thống tự động chấm và nhận xét",
      icon: Brain,
    },
    {
      step: "4",
      title: "Xuất kết quả",
      description: "Export PDF và gửi cho học sinh",
      icon: FileOutput,
    },
  ];

  const recentExams = [
    { name: "James", grade: "Lớp 7", subject: "Số học" },
    { name: "James", grade: "Lớp 7", subject: "Hình học" },
    { name: "bài 1", grade: "Lớp 9", subject: "Hình học" },
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-foreground mb-2">Bảng điều khiển</h1>
        <p className="text-muted-foreground">Tổng quan hệ thống chấm bài Toán</p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.label} className="p-6 hover:shadow-lg transition-shadow">
              <div className="flex items-start justify-between">
                <div className="space-y-2">
                  <p className="text-sm font-medium text-muted-foreground">{stat.label}</p>
                  <p className="text-3xl font-bold text-foreground">{stat.value}</p>
                  {stat.change && (
                    <p className="text-xs text-success flex items-center gap-1">
                      <TrendingUp className="h-3 w-3" />
                      {stat.change}
                    </p>
                  )}
                </div>
                <div className={`p-3 rounded-xl ${stat.color}`}>
                  <Icon className="h-6 w-6 text-white" />
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Recent Exams */}
        <Card className="lg:col-span-2 p-6">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
                <FileText className="h-5 w-5 text-primary" />
                Đề thi gần đây
              </h3>
            </div>
            <Button variant="outline" size="sm" asChild>
              <Link to="/exams">Xem tất cả</Link>
            </Button>
          </div>
          <div className="space-y-3">
            {recentExams.map((exam, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between rounded-lg border border-border bg-muted/30 p-4 hover:bg-muted/50 transition-colors"
              >
                <div className="space-y-1">
                  <p className="font-medium text-foreground">{exam.name}</p>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <span>{exam.grade}</span>
                    <span>•</span>
                    <span>{exam.subject}</span>
                  </div>
                </div>
                <Button variant="ghost" size="sm" asChild>
                  <Link to="/exams">Xem chi tiết</Link>
                </Button>
              </div>
            ))}
          </div>
        </Card>

        {/* Quick Guide */}
        <Card className="p-6 bg-gradient-primary text-primary-foreground">
          <h3 className="mb-6 text-lg font-semibold">Hướng dẫn nhanh</h3>
          <div className="space-y-4">
            {guides.map((guide) => {
              const Icon = guide.icon;
              return (
                <div key={guide.step} className="flex gap-4">
                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-white/20 font-bold">
                    {guide.step}
                  </div>
                  <div className="space-y-1">
                    <p className="font-medium">{guide.title}</p>
                    <p className="text-sm opacity-90">{guide.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      </div>
    </div>
  );
};

export default Dashboard;
