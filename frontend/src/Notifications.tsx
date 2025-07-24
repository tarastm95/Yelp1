import { useSearchParams } from 'react-router-dom';
import NotificationSettings from './NotificationSettings';

const Notifications = () => {
  const [params] = useSearchParams();
  const businessId = params.get('business_id') || undefined;
  return <NotificationSettings businessId={businessId} />;
};

export default Notifications;
