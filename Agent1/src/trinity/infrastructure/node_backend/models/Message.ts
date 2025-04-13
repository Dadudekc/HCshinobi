import mongoose, { Document, Schema } from 'mongoose';

export interface IMessage extends Document {
  chat: mongoose.Types.ObjectId;
  sender: mongoose.Types.ObjectId;
  content: string;
  type: 'text' | 'image' | 'file' | 'system' | 'agent';
  attachments?: {
    url: string;
    type: string;
    size: number;
    name: string;
  }[];
  readBy: {
    userId: mongoose.Types.ObjectId;
    readAt: Date;
  }[];
  metadata: {
    [key: string]: any;
  };
  createdAt: Date;
  updatedAt: Date;
}

const messageSchema = new Schema<IMessage>(
  {
    chat: {
      type: Schema.Types.ObjectId,
      ref: 'Chat',
      required: true,
    },
    sender: {
      type: Schema.Types.ObjectId,
      ref: 'User',
      required: true,
    },
    content: {
      type: String,
      required: true,
      trim: true,
    },
    type: {
      type: String,
      enum: ['text', 'image', 'file', 'system', 'agent'],
      default: 'text',
    },
    attachments: [{
      url: String,
      type: String,
      size: Number,
      name: String,
    }],
    readBy: [{
      userId: {
        type: Schema.Types.ObjectId,
        ref: 'User',
      },
      readAt: {
        type: Date,
        default: Date.now,
      },
    }],
    metadata: {
      type: Schema.Types.Mixed,
      default: {},
    },
  },
  {
    timestamps: true,
  }
);

// Indexes for efficient querying
messageSchema.index({ chat: 1, createdAt: -1 });
messageSchema.index({ sender: 1 });
messageSchema.index({ type: 1 });
messageSchema.index({ 'readBy.userId': 1 });

// Method to mark message as read by a user
messageSchema.methods.markAsRead = function(userId: mongoose.Types.ObjectId): void {
  if (!this.readBy.some(entry => entry.userId.equals(userId))) {
    this.readBy.push({ userId, readAt: new Date() });
  }
};

// Method to check if message is read by a user
messageSchema.methods.isReadBy = function(userId: mongoose.Types.ObjectId): boolean {
  return this.readBy.some(entry => entry.userId.equals(userId));
};

// Method to get unread count for a chat
messageSchema.statics.getUnreadCount = async function(
  chatId: mongoose.Types.ObjectId,
  userId: mongoose.Types.ObjectId
): Promise<number> {
  return this.countDocuments({
    chat: chatId,
    'readBy.userId': { $ne: userId },
    sender: { $ne: userId },
  });
};

export const Message = mongoose.model<IMessage>('Message', messageSchema); 