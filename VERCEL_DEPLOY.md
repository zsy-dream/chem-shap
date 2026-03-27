# ChemSHAP Vercel Deployment

## 部署步骤

### 1. 安装 Vercel CLI
```bash
npm i -g vercel
```

### 2. 登录 Vercel
```bash
vercel login
```

### 3. 部署
```bash
vercel
```

### 4. 生产环境部署
```bash
vercel --prod
```

## 注意事项

⚠️ **重要提示**: 此应用依赖大量机器学习库（numpy, scikit-learn, xgboost, lightgbm, shap），Vercel免费版有100MB部署大小限制，可能无法完整部署。

如需完整功能演示，建议使用:
- **Railway** (支持Docker)
- **Render** (支持Python)
- **阿里云/腾讯云服务器**
