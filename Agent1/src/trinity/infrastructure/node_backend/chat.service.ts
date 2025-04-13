import { Chat, IChat } from '../models/Chat';
import { IMessage, Message } from '../models/Message';

import { User } from '../models/User';

export class ChatService {
  private static instance: ChatService;

  private constructor() {}

  public static getInstance(): ChatService {
    if (!ChatService.instance) {
      ChatService.instance = new ChatService();
    }
    return ChatService.instance;
  }

  public async createChat(
    participants: string[],
    type: 'direct' | 'group' | 'agent',
    name?: string,
    description?: string
  ): Promise<IChat> {
    // Validate participants
    const users = await User.find({ _id: { $in: participants } });
    if (users.length !== participants.length) {
      throw new Error('One or more participants not found');
    }

    // For direct chats, check if it already exists
    if (type === 'direct' && participants.length === 2) {
      const existingChat = await Chat.findOne({
        type: 'direct',
        participants: { $all: participants },
      });

      if (existingChat) {
        return existingChat;
      }
    }

    const chat = new Chat({
      participants,
      type,
      name,
      description,
    });

    await chat.save();
    return chat;
  }

  public async sendMessage(
    chatId: string,
    senderId: string,
    content: string,
    type: 'text' | 'image' | 'file' | 'system' | 'agent' = 'text',
    attachments?: { url: string; type: string; size: number; name: string }[]
  ): Promise<IMessage> {
    const chat = await Chat.findById(chatId);
    if (!chat) {
      throw new Error('Chat not found');
    }

    if (!chat.isParticipant(senderId)) {
      throw new Error('Sender is not a participant in this chat');
    }

    const message = new Message({
      chat: chatId,
      sender: senderId,
      content,
      type,
      attachments,
    });

    await message.save();

    // Update chat's last message
    chat.lastMessage = message._id;
    await chat.save();

    return message;
  }

  public async getChatMessages(
    chatId: string,
    userId: string,
    limit: number = 50,
    before?: string
  ): Promise<IMessage[]> {
    const chat = await Chat.findById(chatId);
    if (!chat) {
      throw new Error('Chat not found');
    }

    if (!chat.isParticipant(userId)) {
      throw new Error('User is not a participant in this chat');
    }

    const query: any = { chat: chatId };
    if (before) {
      query._id = { $lt: before };
    }

    const messages = await Message.find(query)
      .sort({ createdAt: -1 })
      .limit(limit)
      .populate('sender', 'username email')
      .exec();

    // Mark messages as read
    await Message.updateMany(
      {
        _id: { $in: messages.map(m => m._id) },
        'readBy.userId': { $ne: userId },
        sender: { $ne: userId },
      },
      { $push: { readBy: { userId, readAt: new Date() } } }
    );

    return messages.reverse();
  }

  public async getChats(userId: string): Promise<IChat[]> {
    return Chat.find({ participants: userId })
      .populate('participants', 'username email')
      .populate('lastMessage')
      .sort({ updatedAt: -1 })
      .exec();
  }

  public async getUnreadCount(chatId: string, userId: string): Promise<number> {
    return Message.getUnreadCount(chatId, userId);
  }

  public async addParticipant(chatId: string, userId: string, newParticipantId: string): Promise<void> {
    const chat = await Chat.findById(chatId);
    if (!chat) {
      throw new Error('Chat not found');
    }

    if (!chat.isParticipant(userId)) {
      throw new Error('User is not a participant in this chat');
    }

    if (chat.type === 'direct') {
      throw new Error('Cannot add participants to a direct chat');
    }

    const newParticipant = await User.findById(newParticipantId);
    if (!newParticipant) {
      throw new Error('New participant not found');
    }

    chat.addParticipant(newParticipantId);
    await chat.save();
  }

  public async removeParticipant(chatId: string, userId: string, participantId: string): Promise<void> {
    const chat = await Chat.findById(chatId);
    if (!chat) {
      throw new Error('Chat not found');
    }

    if (!chat.isParticipant(userId)) {
      throw new Error('User is not a participant in this chat');
    }

    if (chat.type === 'direct') {
      throw new Error('Cannot remove participants from a direct chat');
    }

    chat.removeParticipant(participantId);
    await chat.save();
  }

  public async updateChat(
    chatId: string,
    userId: string,
    updates: { name?: string; description?: string }
  ): Promise<IChat> {
    const chat = await Chat.findById(chatId);
    if (!chat) {
      throw new Error('Chat not found');
    }

    if (!chat.isParticipant(userId)) {
      throw new Error('User is not a participant in this chat');
    }

    if (updates.name) chat.name = updates.name;
    if (updates.description) chat.description = updates.description;

    await chat.save();
    return chat;
  }
}

export default ChatService.getInstance(); 