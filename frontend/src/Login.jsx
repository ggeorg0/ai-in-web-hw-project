import { useState } from "react";
import { Button, Card, Input, Typography, message } from "antd";
import { ShoppingCartOutlined } from "@ant-design/icons";
import { register, setUserId } from "./api";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    const name = username.trim();
    if (!name) return;
    setLoading(true);
    try {
      const data = await register(name);
      setUserId(data.user_id);
      onLogin(data.user_id);
    } catch {
      message.error("Ошибка регистрации");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh", background: "#f0f2f5" }}>
      <Card style={{ width: 360 }}>
        <div style={{ textAlign: "center", marginBottom: 16 }}>
          <ShoppingCartOutlined style={{ fontSize: 48, color: "#1677ff" }} />
        </div>
        <Typography.Title level={4} style={{ textAlign: "center", marginBottom: 16 }}>
          Список покупок
        </Typography.Title>
        <Input
          placeholder="Имя пользователя"
          size="large"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          onPressEnter={submit}
          style={{ marginBottom: 12 }}
        />
        <Button type="primary" size="large" block loading={loading} onClick={submit}>
          Начать
        </Button>
      </Card>
    </div>
  );
}
