// MongoDB initialization script for Speecher development environment
// This script runs when the MongoDB container is first created

// Switch to the speecher_dev database
db = db.getSiblingDB('speecher_dev');

// Create collections with validation schemas
db.createCollection('users', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['email', 'username', 'passwordHash', 'role', 'createdAt'],
            properties: {
                _id: {
                    bsonType: 'objectId'
                },
                email: {
                    bsonType: 'string',
                    pattern: '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$',
                    description: 'Valid email address required'
                },
                username: {
                    bsonType: 'string',
                    minLength: 3,
                    maxLength: 50,
                    description: 'Username between 3-50 characters'
                },
                passwordHash: {
                    bsonType: 'string',
                    description: 'Hashed password'
                },
                fullName: {
                    bsonType: 'string',
                    maxLength: 255
                },
                role: {
                    enum: ['admin', 'user', 'guest'],
                    description: 'User role'
                },
                isActive: {
                    bsonType: 'bool'
                },
                isVerified: {
                    bsonType: 'bool'
                },
                createdAt: {
                    bsonType: 'date'
                },
                updatedAt: {
                    bsonType: 'date'
                },
                lastLogin: {
                    bsonType: 'date'
                },
                metadata: {
                    bsonType: 'object'
                }
            }
        }
    }
});

db.createCollection('audioFiles', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['userId', 'filename', 'uploadedAt'],
            properties: {
                _id: {
                    bsonType: 'objectId'
                },
                userId: {
                    bsonType: 'objectId',
                    description: 'Reference to user'
                },
                filename: {
                    bsonType: 'string',
                    maxLength: 500
                },
                originalFilename: {
                    bsonType: 'string',
                    maxLength: 500
                },
                fileSize: {
                    bsonType: 'long',
                    minimum: 0
                },
                durationSeconds: {
                    bsonType: 'double',
                    minimum: 0
                },
                format: {
                    bsonType: 'string',
                    maxLength: 50
                },
                sampleRate: {
                    bsonType: 'int'
                },
                channels: {
                    bsonType: 'int',
                    minimum: 1,
                    maximum: 8
                },
                bitrate: {
                    bsonType: 'int'
                },
                storagePath: {
                    bsonType: 'string'
                },
                storageProvider: {
                    enum: ['local', 'aws', 'azure', 'gcp'],
                    description: 'Storage provider'
                },
                status: {
                    enum: ['pending', 'processing', 'completed', 'failed'],
                    description: 'Processing status'
                },
                uploadedAt: {
                    bsonType: 'date'
                },
                processedAt: {
                    bsonType: 'date'
                },
                metadata: {
                    bsonType: 'object'
                }
            }
        }
    }
});

db.createCollection('transcriptions', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['audioFileId', 'userId', 'createdAt'],
            properties: {
                _id: {
                    bsonType: 'objectId'
                },
                audioFileId: {
                    bsonType: 'objectId',
                    description: 'Reference to audio file'
                },
                userId: {
                    bsonType: 'objectId',
                    description: 'Reference to user'
                },
                text: {
                    bsonType: 'string'
                },
                language: {
                    bsonType: 'string',
                    maxLength: 10
                },
                confidenceScore: {
                    bsonType: 'double',
                    minimum: 0,
                    maximum: 1
                },
                wordCount: {
                    bsonType: 'int',
                    minimum: 0
                },
                status: {
                    enum: ['pending', 'processing', 'completed', 'failed', 'cancelled'],
                    description: 'Transcription status'
                },
                engine: {
                    bsonType: 'string',
                    maxLength: 50
                },
                engineVersion: {
                    bsonType: 'string',
                    maxLength: 50
                },
                processingTimeMs: {
                    bsonType: 'int',
                    minimum: 0
                },
                createdAt: {
                    bsonType: 'date'
                },
                completedAt: {
                    bsonType: 'date'
                },
                metadata: {
                    bsonType: 'object'
                },
                wordTimestamps: {
                    bsonType: 'array',
                    items: {
                        bsonType: 'object',
                        required: ['word', 'startTime', 'endTime'],
                        properties: {
                            word: {
                                bsonType: 'string'
                            },
                            startTime: {
                                bsonType: 'double',
                                minimum: 0
                            },
                            endTime: {
                                bsonType: 'double',
                                minimum: 0
                            },
                            confidence: {
                                bsonType: 'double',
                                minimum: 0,
                                maximum: 1
                            },
                            speakerId: {
                                bsonType: 'string'
                            }
                        }
                    }
                }
            }
        }
    }
});

db.createCollection('sessions', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['userId', 'token', 'createdAt', 'expiresAt'],
            properties: {
                _id: {
                    bsonType: 'objectId'
                },
                userId: {
                    bsonType: 'objectId',
                    description: 'Reference to user'
                },
                token: {
                    bsonType: 'string',
                    maxLength: 500
                },
                ipAddress: {
                    bsonType: 'string'
                },
                userAgent: {
                    bsonType: 'string'
                },
                createdAt: {
                    bsonType: 'date'
                },
                expiresAt: {
                    bsonType: 'date'
                },
                lastActivity: {
                    bsonType: 'date'
                },
                isActive: {
                    bsonType: 'bool'
                }
            }
        }
    }
});

db.createCollection('apiKeys', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['userId', 'keyHash', 'createdAt'],
            properties: {
                _id: {
                    bsonType: 'objectId'
                },
                userId: {
                    bsonType: 'objectId',
                    description: 'Reference to user'
                },
                keyHash: {
                    bsonType: 'string',
                    maxLength: 255
                },
                name: {
                    bsonType: 'string',
                    maxLength: 255
                },
                permissions: {
                    bsonType: 'array',
                    items: {
                        bsonType: 'string'
                    }
                },
                rateLimit: {
                    bsonType: 'int',
                    minimum: 0
                },
                createdAt: {
                    bsonType: 'date'
                },
                expiresAt: {
                    bsonType: 'date'
                },
                lastUsedAt: {
                    bsonType: 'date'
                },
                isActive: {
                    bsonType: 'bool'
                }
            }
        }
    }
});

db.createCollection('activityLog', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['action', 'createdAt'],
            properties: {
                _id: {
                    bsonType: 'objectId'
                },
                userId: {
                    bsonType: 'objectId',
                    description: 'Reference to user'
                },
                action: {
                    bsonType: 'string',
                    maxLength: 100
                },
                entityType: {
                    bsonType: 'string',
                    maxLength: 100
                },
                entityId: {
                    bsonType: 'objectId'
                },
                oldValues: {
                    bsonType: 'object'
                },
                newValues: {
                    bsonType: 'object'
                },
                ipAddress: {
                    bsonType: 'string'
                },
                userAgent: {
                    bsonType: 'string'
                },
                createdAt: {
                    bsonType: 'date'
                },
                metadata: {
                    bsonType: 'object'
                }
            }
        }
    },
    capped: true,
    size: 104857600, // 100MB
    max: 1000000 // Maximum 1 million documents
});

// Create indexes for better performance
db.users.createIndex({ email: 1 }, { unique: true });
db.users.createIndex({ username: 1 }, { unique: true });
db.users.createIndex({ createdAt: -1 });
db.users.createIndex({ role: 1, isActive: 1 });

db.audioFiles.createIndex({ userId: 1 });
db.audioFiles.createIndex({ status: 1 });
db.audioFiles.createIndex({ uploadedAt: -1 });
db.audioFiles.createIndex({ filename: 1 });

db.transcriptions.createIndex({ audioFileId: 1 });
db.transcriptions.createIndex({ userId: 1 });
db.transcriptions.createIndex({ status: 1 });
db.transcriptions.createIndex({ createdAt: -1 });
db.transcriptions.createIndex({ language: 1 });
// Text search index for transcriptions
db.transcriptions.createIndex({ text: 'text' });

db.sessions.createIndex({ userId: 1 });
db.sessions.createIndex({ token: 1 }, { unique: true });
db.sessions.createIndex({ expiresAt: 1 });
db.sessions.createIndex({ isActive: 1, expiresAt: 1 });

db.apiKeys.createIndex({ userId: 1 });
db.apiKeys.createIndex({ keyHash: 1 }, { unique: true });
db.apiKeys.createIndex({ isActive: 1 });

db.activityLog.createIndex({ userId: 1 });
db.activityLog.createIndex({ createdAt: -1 });
db.activityLog.createIndex({ entityType: 1, entityId: 1 });
db.activityLog.createIndex({ action: 1 });

// Create initial admin user
// Note: In production, passwords should be properly hashed
db.users.insertOne({
    email: 'admin@speecher.local',
    username: 'admin',
    passwordHash: '$2b$12$LQiY3YjgRRKmRCBQH8KBHO5kZiHzYYKpDsZxYYGLRrcvP5zLrXVKa', // admin123
    fullName: 'System Administrator',
    role: 'admin',
    isActive: true,
    isVerified: true,
    createdAt: new Date(),
    updatedAt: new Date(),
    metadata: {
        createdBy: 'system',
        source: 'initialization'
    }
});

// Create read-only user for analytics (optional)
db.createUser({
    user: 'speecher_readonly',
    pwd: 'readonly_pass_dev',
    roles: [
        {
            role: 'read',
            db: 'speecher_dev'
        }
    ]
});

// Create application user with read/write permissions
db.createUser({
    user: 'speecher_app',
    pwd: 'app_pass_dev',
    roles: [
        {
            role: 'readWrite',
            db: 'speecher_dev'
        }
    ]
});

// Create test database
db = db.getSiblingDB('speecher_test');

// Copy schema to test database
db.createCollection('users');
db.createCollection('audioFiles');
db.createCollection('transcriptions');
db.createCollection('sessions');
db.createCollection('apiKeys');
db.createCollection('activityLog');

// Create test user for test database
db.createUser({
    user: 'speecher_test',
    pwd: 'test_pass_dev',
    roles: [
        {
            role: 'readWrite',
            db: 'speecher_test'
        }
    ]
});

// Print success message
print('MongoDB initialization completed successfully for Speecher');
print('Databases created: speecher_dev, speecher_test');
print('Default admin user created: admin@speecher.local / admin123');
print('Please change the admin password immediately!');