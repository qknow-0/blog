# OpenSSL 证书操作实战

> 基于 OpenSSL 3.x，macOS 自带（`/usr/bin/openssl`）。

## 为什么抓包需要懂证书

mitmproxy 抓 HTTPS 的流程是：生成假证书 → 让系统信任它 → 拦截连接。每一步都涉及证书操作。OpenSSL 是处理证书的瑞士军刀——生成、转换、查看，全用它。

## 证书格式速查

| 格式 | 后缀 | 内容 | 用途 |
|------|------|------|------|
| PEM | `.pem` `.crt` `.key` | Base64 编码的文本，`-----BEGIN...-----` 包裹 | Linux/macOS 通用 |
| DER | `.der` `.cer` | 二进制格式 | macOS Keychain、Windows |
| PKCS#12 | `.p12` `.pfx` | 二进制，证书 + 私钥打包 | 浏览器导入导出 |
| PKCS#7 | `.p7b` | 证书链（不含私钥） | Windows IIS |

日常最常用的是 PEM——纯文本，`cat` 就能看。macOS Keychain 只接受 DER，所以往系统装证书时需要转格式。

## 查看证书内容

```bash
# 查看 PEM 证书的全部信息
openssl x509 -in cert.pem -text -noout
```

输出示例：

```
Certificate:
    Data:
        Version: 3
        Serial Number: ab:cd:ef:...
        Signature Algorithm: sha256WithRSAEncryption
        Issuer: CN=mitmproxy, O=mitmproxy
        Validity
            Not Before: Jun 10 00:00:00 2026 GMT
            Not After : Jun 10 00:00:00 2029 GMT
        Subject: CN=*.example.com
        Subject Public Key Info:
            Public Key Algorithm: rsaEncryption
                RSA Public-Key: (2048 bit)
                Modulus: ...
```

### 只看特定字段

```bash
# 只看主题（域名）
openssl x509 -in cert.pem -subject -noout
# subject=CN=*.ztqft.com

# 只看过期时间
openssl x509 -in cert.pem -enddate -noout
# notAfter=Jun 10 00:00:00 2029 GMT

# 只看指纹
openssl x509 -in cert.pem -fingerprint -noout
# SHA1 Fingerprint=AB:CD:EF:...

# SHA256 指纹（证书锁定的依据）
openssl x509 -in cert.pem -fingerprint -sha256 -noout
```

### 查看远程服务的证书

```bash
# 连接服务器，获取它的证书信息
openssl s_client -connect smarttest.ztqft.com:443 -showcerts
```

这个命令打印 TLS 握手全过程，包括服务器发来的证书链。结合上面的 `openssl x509` 就能提取指纹、有效期等关键信息。如果你在做证书锁定分析，这是第一步——先搞清楚服务器证书长什么样。

## 格式转换

### PEM → DER（往 macOS Keychain 导入）

```bash
openssl x509 -in mitmproxy-ca-cert.pem -outform DER -out mitmproxy-ca-cert.der
```

导出后双击 `.der` 文件，Keychain Access 自动弹出导入向导。

### DER → PEM

```bash
openssl x509 -in cert.der -inform DER -out cert.pem
```

### PEM → PKCS#12（证书 + 私钥打包）

```bash
openssl pkcs12 -export \
  -in cert.pem \
  -inkey key.pem \
  -out bundle.p12 \
  -name "My Certificate"
```

### 查看 PKCS#12 文件内容

```bash
openssl pkcs12 -in bundle.p12 -info -noout
```

## 生成自签名证书

自签名证书在本地开发或中间人代理（mitmproxy）场景中需要。

### 生成 CA 证书

```bash
# 1. 生成私钥
openssl genrsa -out ca.key 2048

# 2. 生成自签名 CA 证书（有效期 3 年）
openssl req -x509 -new -nodes \
  -key ca.key \
  -sha256 \
  -days 1095 \
  -out ca.pem \
  -subj "/CN=My Local CA/O=Development/C=CN"

# CN: Common Name（证书名称）
# O:  Organization（组织）
# C:  Country（国家）
```

### 为域名签发证书

```bash
# 1. 生成域名私钥
openssl genrsa -out server.key 2048

# 2. 生成 CSR（证书签名请求）
openssl req -new -key server.key -out server.csr -subj "/CN=api.example.com"

# 3. 用 CA 证书签发
openssl x509 -req -in server.csr \
  -CA ca.pem \
  -CAkey ca.key \
  -CAcreateserial \
  -out server.pem \
  -days 365 \
  -sha256
```

这样 `server.pem` 就是一个被你的私有 CA 签发的有效证书。浏览器信任它需要先信任 `ca.pem`。

### 生成支持多个域名（SAN）的证书

```bash
cat > san.cnf << 'EOF'
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req

[req_distinguished_name]
CN = example.com

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = example.com
DNS.2 = api.example.com
DNS.3 = *.example.com
EOF

openssl req -x509 -new -nodes \
  -key server.key \
  -sha256 \
  -days 365 \
  -out server.pem \
  -config san.cnf \
  -extensions v3_req
```

## 验证证书链

```bash
# 验证一个证书是否由指定的 CA 签发
openssl verify -CAfile ca.pem server.pem

# 验证带中间证书的链
openssl verify -CAfile root-ca.pem -untrusted intermediate.pem server.pem
```

输出 `OK` 表示验证通过；否则打印错误信息（证书过期、CA 不匹配、用途不匹配等）。

## 提取公钥

```bash
# 从证书中提取公钥
openssl x509 -in cert.pem -pubkey -noout

# 从私钥中提取公钥
openssl rsa -in key.pem -pubout
```

## 加密与签名（非证书相关但常用）

```bash
# 对称加密文件
openssl enc -aes-256-cbc -salt -in plain.txt -out encrypted.bin
# 解密
openssl enc -d -aes-256-cbc -in encrypted.bin -out plain.txt

# 计算文件的 SHA256 哈希
openssl dgst -sha256 file.bin

# Base64 编码/解码
echo -n "hello" | openssl base64     # aGVsbG8=
echo "aGVsbG8=" | openssl base64 -d  # hello
```

## 小结

OpenSSL 在抓包流程中的角色很明确——处理证书格式转换和信任链。最常用的就三个操作：

| 操作 | 命令 |
|------|------|
| 查看证书 | `openssl x509 -in cert.pem -text -noout` |
| PEM → DER | `openssl x509 -in cert.pem -outform DER -out cert.der` |
| 远程服务证书 | `openssl s_client -connect host:443 -showcerts` |

下一篇：**tcpdump + Wireshark**——连 TLS 都解不开的时候，还能看什么。
