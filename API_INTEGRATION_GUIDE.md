# 贾丹照片管理 API 前端集成指南

## 🚀 快速开始

### API 文档地址
启动服务器后，访问：**http://localhost:5000/api/docs/**

这是一个完整的 Swagger UI 界面，包含所有 API 的详细文档、参数说明和在线测试功能。

### 安装和启动

```bash
# 安装依赖
pip install -r requirements.txt

# 启动 OpenAPI 版本
python run_openapi.py
```

## 📋 API 概览

### 基础信息
- **Base URL**: `http://localhost:5000/api`
- **认证方式**: JWT Bearer Token
- **数据格式**: JSON
- **文件上传**: multipart/form-data

### API 分组
1. **认证接口** (`/auth`) - 用户登录、登出、验证
2. **照片管理** (`/photos`) - 照片 CRUD 操作
3. **公开接口** (`/public`) - 无需认证的照片浏览
4. **仪表板** (`/dashboard`) - 统计信息

## 🔐 认证流程

### 1. 用户登录
```javascript
// POST /api/auth/login
const loginResponse = await fetch('/api/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    username: 'admin',
    password: 'admin123'
  })
});

const { success, data } = await loginResponse.json();
if (success) {
  const token = data.token;
  // 保存 token 到 localStorage 或其他存储
  localStorage.setItem('authToken', token);
}
```

### 2. 使用 Token 进行认证
```javascript
const token = localStorage.getItem('authToken');

const authenticatedRequest = await fetch('/api/photos', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});
```

### 3. Token 验证
```javascript
// GET /api/auth/verify
const verifyResponse = await fetch('/api/auth/verify', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

## 📸 照片管理操作

### 1. 获取照片列表
```javascript
// GET /api/photos?page=1&per_page=12&search=关键词
const getPhotos = async (page = 1, perPage = 12, search = '') => {
  const params = new URLSearchParams({
    page: page.toString(),
    per_page: perPage.toString(),
    ...(search && { search })
  });
  
  const response = await fetch(`/api/photos?${params}`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  return response.json();
};
```

### 2. 上传照片
```javascript
// POST /api/photos/upload
const uploadPhoto = async (file, metadata = {}) => {
  const formData = new FormData();
  formData.append('file', file);
  
  // 可选的元数据
  if (metadata.title) formData.append('title', metadata.title);
  if (metadata.description) formData.append('description', metadata.description);
  if (metadata.date) formData.append('date', metadata.date);
  if (metadata.location) formData.append('location', metadata.location);
  if (metadata.is_public !== undefined) formData.append('is_public', metadata.is_public);
  
  const response = await fetch('/api/photos/upload', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData
  });
  
  return response.json();
};
```

### 3. 更新照片信息
```javascript
// PUT /api/photos/{photo_id}
const updatePhoto = async (photoId, updates) => {
  const response = await fetch(`/api/photos/${photoId}`, {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(updates)
  });
  
  return response.json();
};
```

### 4. 删除照片
```javascript
// DELETE /api/photos/{photo_id}
const deletePhoto = async (photoId) => {
  const response = await fetch(`/api/photos/${photoId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  return response.json();
};
```

## 🌐 公开接口（无需认证）

### 获取公开照片
```javascript
// GET /api/public/photos?page=1&per_page=12
const getPublicPhotos = async (page = 1, perPage = 12) => {
  const params = new URLSearchParams({
    page: page.toString(),
    per_page: perPage.toString()
  });
  
  const response = await fetch(`/api/public/photos?${params}`);
  return response.json();
};
```

## 📊 仪表板统计
```javascript
// GET /api/dashboard/stats
const getDashboardStats = async () => {
  const response = await fetch('/api/dashboard/stats', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  return response.json();
};
```

## 🎯 React/Vue 示例组件

### React Hook 示例
```jsx
import { useState, useEffect } from 'react';

const usePhotoAPI = () => {
  const [token, setToken] = useState(localStorage.getItem('authToken'));
  
  const apiCall = async (url, options = {}) => {
    const defaultOptions = {
      headers: {
        ...(token && { 'Authorization': `Bearer ${token}` }),
        'Content-Type': 'application/json',
        ...options.headers
      }
    };
    
    const response = await fetch(`/api${url}`, {
      ...defaultOptions,
      ...options
    });
    
    if (response.status === 401) {
      // Token 过期，清除本地存储
      localStorage.removeItem('authToken');
      setToken(null);
      throw new Error('Authentication required');
    }
    
    return response.json();
  };
  
  const login = async (username, password) => {
    const result = await apiCall('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
    
    if (result.success) {
      const newToken = result.data.token;
      localStorage.setItem('authToken', newToken);
      setToken(newToken);
    }
    
    return result;
  };
  
  const getPhotos = (params) => apiCall(`/photos?${new URLSearchParams(params)}`);
  const uploadPhoto = (formData) => apiCall('/photos/upload', {
    method: 'POST',
    body: formData,
    headers: {} // 让浏览器自动设置 Content-Type
  });
  
  return { login, getPhotos, uploadPhoto, apiCall, isAuthenticated: !!token };
};
```

### Vue 3 Composable 示例
```javascript
import { ref, computed } from 'vue';

export const usePhotoAPI = () => {
  const token = ref(localStorage.getItem('authToken'));
  const isAuthenticated = computed(() => !!token.value);
  
  const apiCall = async (url, options = {}) => {
    const defaultOptions = {
      headers: {
        ...(token.value && { 'Authorization': `Bearer ${token.value}` }),
        'Content-Type': 'application/json',
        ...options.headers
      }
    };
    
    const response = await fetch(`/api${url}`, {
      ...defaultOptions,
      ...options
    });
    
    if (response.status === 401) {
      localStorage.removeItem('authToken');
      token.value = null;
      throw new Error('Authentication required');
    }
    
    return response.json();
  };
  
  const login = async (username, password) => {
    const result = await apiCall('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
    
    if (result.success) {
      const newToken = result.data.token;
      localStorage.setItem('authToken', newToken);
      token.value = newToken;
    }
    
    return result;
  };
  
  return { login, apiCall, isAuthenticated };
};
```

## 🔧 TypeScript 类型定义

```typescript
// API 响应基础类型
interface BaseResponse {
  success: boolean;
  message?: string;
}

interface ErrorResponse extends BaseResponse {
  success: false;
  error: {
    code: string;
    message: string;
    details: string;
  };
}

// 用户相关类型
interface User {
  id: number;
  username: string;
  email: string;
}

interface LoginResponse extends BaseResponse {
  success: true;
  data: {
    token: string;
    user: User;
  };
}

// 照片相关类型
interface Photo {
  id: string;
  title: string;
  description?: string;
  src: string;
  thumbnail: string;
  date?: string;
  size: string;
  location?: string;
  is_public: boolean;
  file_name: string;
  mime_type: string;
  created_at: string;
  updated_at: string;
}

interface PhotosResponse extends BaseResponse {
  success: true;
  data: {
    photos: Photo[];
    pagination: {
      page: number;
      per_page: number;
      total: number;
      pages: number;
    };
  };
}

interface PhotoUploadData {
  title?: string;
  description?: string;
  date?: string;
  location?: string;
  is_public?: boolean;
}
```

## ⚠️ 错误处理

API 返回统一的错误格式：
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "用户友好的错误信息",
    "details": "详细的错误描述"
  }
}
```

常见错误代码：
- `UNAUTHORIZED`: 未认证或 token 无效
- `FORBIDDEN`: 无权限访问
- `NOT_FOUND`: 资源不存在
- `INVALID_FILE_TYPE`: 不支持的文件类型
- `FILE_TOO_LARGE`: 文件过大

## 📝 最佳实践

1. **Token 管理**: 建议在请求拦截器中统一处理 token
2. **错误处理**: 实现全局错误处理，自动处理 401 状态码
3. **文件上传**: 显示上传进度，支持取消上传
4. **缓存**: 合理缓存照片列表和用户信息
5. **分页**: 实现虚拟滚动或分页加载

## 🔗 相关链接

- [Swagger UI 文档](http://localhost:5000/api/docs/)
- [OpenAPI 规范](https://swagger.io/specification/)
- [JWT 认证](https://jwt.io/)

## ❓ 常见问题

**Q: 如何处理文件上传进度？**
A: 使用 XMLHttpRequest 替代 fetch，监听 upload.progress 事件。

**Q: Token 过期如何处理？**
A: 监听 401 响应，自动清除本地 token 并跳转到登录页。

**Q: 如何优化图片加载？**
A: 使用缩略图 (thumbnail) 字段进行预览，点击后加载原图 (src)。 