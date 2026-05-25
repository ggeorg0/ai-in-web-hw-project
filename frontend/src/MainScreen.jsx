import { useState, useEffect, useRef, useCallback } from "react";
import { Button, Card, List, Typography, message, Tag } from "antd";
import { AudioOutlined, DeleteOutlined, LogoutOutlined, LoadingOutlined } from "@ant-design/icons";
import { getShoppingList, uploadVoice, getTaskStatus, addItem, deleteItem } from "./api";

export default function MainScreen({ onLogout }) {
  const [items, setItems] = useState([]);
  const [recording, setRecording] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState("");
  const mrRef = useRef(null);
  const chunksRef = useRef([]);

  const loadList = useCallback(async () => {
    try {
      const data = await getShoppingList();
      setItems(data.items);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { loadList(); }, [loadList]);

  const processAudio = async (blob) => {
    setProcessing(true);
    try {
      const { task_id } = await uploadVoice(blob);
      let attempts = 0;
      let pollErrors = 0;
      const poll = async () => {
        attempts++;
        try {
          const status = await getTaskStatus(task_id);

          if (status.status === "completed") {
            for (const product of status.extracted_products || []) {
              await addItem(product);
            }
            await loadList();
            setProcessing(false);
          } else if (status.status === "failed") {
            setError(status.error || "Ошибка обработки");
            setProcessing(false);
          } else if (attempts < 60) {
            setTimeout(poll, 1000);
          } else {
            setError("Таймаут обработки");
            setProcessing(false);
          }
        } catch {
          pollErrors++;
          if (pollErrors < 3) {
            setTimeout(poll, 1000);
          } else {
            setError("Ошибка проверки статуса");
            setProcessing(false);
          }
        }
      };
      poll();
    } catch {
      setError("Ошибка при отправке аудио");
      setProcessing(false);
    }
  };

  const start = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      chunksRef.current = [];

      mr.ondataavailable = (e) => chunksRef.current.push(e.data);
      mr.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        processAudio(new Blob(chunksRef.current, { type: "audio/webm" }));
      };

      mrRef.current = mr;
      mr.start();
      setRecording(true);
      setError("");
    } catch {
      message.error("Нет доступа к микрофону");
    }
  };

  const stop = () => {
    mrRef.current?.stop();
    setRecording(false);
  };

  const handleDelete = async (id) => {
    try {
      await deleteItem(id);
      setItems((prev) => prev.filter((i) => i.id !== id));
    } catch { /* ignore */ }
  };

  return (
    <div style={{ maxWidth: 500, margin: "0 auto", padding: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>Список покупок</Typography.Title>
        <Button icon={<LogoutOutlined />} onClick={onLogout}>Выйти</Button>
      </div>

      <div style={{ textAlign: "center", marginBottom: 24 }}>
        {processing ? (
          <Button size="large" disabled style={{ minWidth: 200, height: 48 }}>
            <LoadingOutlined /> Обработка...
          </Button>
        ) : recording ? (
          <div>
            <Tag color="red">Запись...</Tag>
            <Button danger onClick={stop} style={{ marginLeft: 8 }}>Стоп</Button>
          </div>
        ) : (
          <Button
            size="large"
            type="primary"
            icon={<AudioOutlined />}
            onClick={start}
            style={{ minWidth: 200, height: 48 }}
          >
            Говорить
          </Button>
        )}
      </div>

      {error && (
        <Card
          size="small"
          style={{ marginBottom: 16, background: "#fff1f0", border: "1px solid #ffa39e" }}
        >
          <Typography.Text type="danger">{error}</Typography.Text>
          <Button size="small" type="link" onClick={() => setError("")} style={{ marginLeft: 8 }}>
            Скрыть
          </Button>
        </Card>
      )}

      <Card title="Ваш список" size="small">
        {items.length === 0 ? (
          <Typography.Text type="secondary">Список пуст</Typography.Text>
        ) : (
          <List
            dataSource={items}
            renderItem={(item) => (
              <List.Item
                actions={[
                  <Button
                    key="del"
                    type="text"
                    danger
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={() => handleDelete(item.id)}
                  />,
                ]}
              >
                {item.product_name}
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  );
}
