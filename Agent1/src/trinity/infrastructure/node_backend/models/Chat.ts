import mongoose, { Document, Schema } from 'mongoose';

export interface IChat extends Document {
  participants: mongoose.Types.ObjectId[];
  type: 'direct' | 'group' | 'agent';
  name?: string;
  description?: string;
  lastMessage?: mongoose.Types.ObjectId;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
  metadata: {
    [key: string]: any;
  };
}

const chatSchema = new Schema<IChat>(
  {
    participants: [{
      type: Schema.Types.ObjectId,
      ref: 'User',
      required: true,
    }],
    type: {
      type: String,
      enum: ['direct', 'group', 'agent'],
      required: true,
    },
    name: {
      type: String,
      trim: true,
      maxlength: 100,
    },
    description: {
      type: String,
      trim: true,
      maxlength: 500,
    },
    lastMessage: {
      type: Schema.Types.ObjectId,
      ref: 'Message',
    },
    isActive: {
      type: Boolean,
      default: true,
    },
    metadata: {
      type: Schema.Types.Mixed,
      default: {},
    },
  },
  {
    timestamps: true,
  }
);

// Indexes
chatSchema.index({ participants: 1 });
chatSchema.index({ type: 1 });
chatSchema.index({ lastMessage: 1 });
chatSchema.index({ isActive: 1 });

// Virtual for getting participant count
chatSchema.virtual('participantCount').get(function() {
  return this.participants.length;
});

// Method to check if a user is a participant
chatSchema.methods.isParticipant = function(userId: mongoose.Types.ObjectId): boolean {
  return this.participants.some(participant => participant.equals(userId));
};

// Method to add a participant
chatSchema.methods.addParticipant = function(userId: mongoose.Types.ObjectId): void {
  if (!this.isParticipant(userId)) {
    this.participants.push(userId);
  }
};

// Method to remove a participant
chatSchema.methods.removeParticipant = function(userId: mongoose.Types.ObjectId): void {
  this.participants = this.participants.filter(
    participant => !participant.equals(userId)
  );
};

export const Chat = mongoose.model<IChat>('Chat', chatSchema); 